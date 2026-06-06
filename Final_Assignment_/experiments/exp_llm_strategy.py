"""Compare zero-shot vs few-shot prompting for building parameter generation"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from dotenv import load_dotenv
from google import genai
from scipy.stats import wilcoxon
from groq import Groq
from scipy.stats import spearmanr

from src.llm.client import BuildingLLM

load_dotenv()

CONCEPTS = [
    #Residential, simple
    "fisherman's cottage by the sea, simple and weathered",
    "small Cycladic cottage with a flower-pot porch",
    "tiny one-room shepherd's hut on a hillside",
    "modest village house with a stone path and chimney",
    #Residential, larger
    "wealthy merchant's two-story house with balcony and ornate trim",
    "two-story Mykonos seaside villa with pergola and rooftop terrace",
    "rustic farmer's house with stone accents and rooftop terrace",
    "spacious family home, white walls, blue shutters, gabled roof",
    #Religious
    "small whitewashed chapel with a prominent blue dome",
    "tiny clifftop chapel with a single cross",
    "blue-domed church with bell tower",
    "village chapel with stone foundation and white dome",
    #Commercial 
    "village tavern, welcoming with broad terrace and decorative trim",
    "small bakery with chimney and shuttered windows",
    "harbour-side fish market, single floor, simple and weathered",
    "blacksmith's workshop with stone walls and rooftop chimney",
    #Special
    "tiny white watchtower overlooking the sea",
    "windmill-style building, tall and narrow, white with blue trim",
]


JUDGE_PROMPT = """You are an architectural critic evaluating a generated building specification
for a Greek Cycladic island village (think Santorini, Mykonos). The specification was generated
by an AI given the concept: "{concept}"

The specification:
{params}

Rate it on three dimensions (1-10 scale, integers):
1. CONCEPT_FIT: how well do the parameters reflect the requested concept?
2. CULTURAL_AUTHENTICITY: how Cycladic does it feel (whitewashed walls, blue accents, simple geometry)?
3. ARCHITECTURAL_COHERENCE: are floors, roof, and decorations sensible together?

Return ONLY a JSON object with this exact shape:
{{"concept_fit": <int>, "cultural_authenticity": <int>, "architectural_coherence": <int>, "comment": "<one-sentence justification>"}}"""

JUDGE_CACHE = Path("data/llm_cache/judge")
JUDGE_CACHE.mkdir(parents=True, exist_ok=True)


"""Caching every response on disk means re-runs are free and quota-exhausted 
runs do not lose progress on subsequent restart"""
def _cache_path(concept, strategy, params_dict):
    blob = f"{concept}|{strategy}|{json.dumps(params_dict, sort_keys=True)}"
    h = hashlib.md5(blob.encode()).hexdigest()[:12]
    return JUDGE_CACHE / f"{h}.json"


def judge_one(client, concept, params_dict, strategy):
    cache_file = _cache_path(concept, strategy, params_dict)
    if cache_file.exists():
        print("    (using cached judge result)")
        return json.loads(cache_file.read_text())

    prompt = JUDGE_PROMPT.format(concept=concept, params=json.dumps(params_dict, indent=2))

    #Try primary model, fall back to flash-lite if rate-limited
    models_to_try = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    last_err = None

    for model_name in models_to_try:
        for attempt in range(3):
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config={"response_mime_type": "application/json"},
                )
                result = json.loads(resp.text)
                result["_judge_model"] = model_name
                cache_file.write_text(json.dumps(result))
                return result
            except Exception as e:
                last_err = e
                err_str = str(e)
                msg = err_str[:90].replace("\n", " ")
                print(f"    [{model_name}] attempt {attempt+1}/3 failed: {type(e).__name__}: {msg}")
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"    Quota exhausted on {model_name}, switching model...")
                    break  # don't waste retries on a quota error
                wait = 5 * (2 ** attempt)
                print(f"    waiting {wait}s before retry...")
                time.sleep(wait)

    raise RuntimeError(f"Judge failed on all models. Last error: {last_err}")


"""Independent judge from a different model family than the generator (Llama 3.3)"""
def judge_one_llama(concept, params_dict, strategy):
    cache_file = JUDGE_CACHE / f"llama_{_cache_path(concept, strategy, params_dict).stem}.json"
    if cache_file.exists():
        print("    (using cached llama judge result)")
        return json.loads(cache_file.read_text())

    client = Groq()  # reads GROQ_API_KEY from env
    prompt = JUDGE_PROMPT.format(concept=concept, params=json.dumps(params_dict, indent=2))

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3,
            )
            text = resp.choices[0].message.content.strip()
            result = json.loads(text)
            
            """Llama occasionally returns scores as strings ("8") instead of
            ints, force to keep downstream pandas dtypes consistent"""
            
            for k in ["concept_fit", "cultural_authenticity", "architectural_coherence"]:
                result[k] = int(result[k])
            result["_judge_model"] = "llama-3.3-70b-versatile"
            cache_file.write_text(json.dumps(result))
            return result
        except Exception as e:
            print(f"    [llama] attempt {attempt+1}/3 failed: {type(e).__name__}: {str(e)[:80]}")
            time.sleep(5 * (2 ** attempt))

    raise RuntimeError(f"Llama judge failed after 3 attempts")



def main():
    llm = BuildingLLM()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    rows = []
    #Each iteration generate params under one strategy, then collect
    #judgements from both raters
    for concept in CONCEPTS:
            for strategy in ["zero_shot", "few_shot"]:
                print(f"[{strategy}] generating: {concept[:55]}...")
                params = llm.generate(concept, strategy=strategy)
                params_dict = params.model_dump() if hasattr(params, "model_dump") else params

                print("  judging with Gemini...")
                gem = judge_one(client, concept, params_dict, strategy)
                print("  judging with Llama...")
                lla = judge_one_llama(concept, params_dict, strategy)

                rows.append({
                    "concept": concept,
                    "strategy": strategy,
                    "gemini_concept_fit": gem["concept_fit"],
                    "gemini_cultural": gem["cultural_authenticity"],
                    "gemini_coherence": gem["architectural_coherence"],
                    "gemini_total": gem["concept_fit"] + gem["cultural_authenticity"] + gem["architectural_coherence"],
                    "gemini_comment": gem["comment"],
                    "llama_concept_fit": lla["concept_fit"],
                    "llama_cultural": lla["cultural_authenticity"],
                    "llama_coherence": lla["architectural_coherence"],
                    "llama_total": lla["concept_fit"] + lla["cultural_authenticity"] + lla["architectural_coherence"],
                    "llama_comment": lla["comment"],
                })
                
                """Gemini free tier allows around 5 requests/minute. Two judge calls
                per iteration means we need about 15s between iterations to stay
                under the rolling per-minute quota"""
                time.sleep(15)   

    Path("results").mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv("results/exp_llm_strategy.csv", index=False)
    print(f"\nSaved: results/exp_llm_strategy.csv")


    print("\n=== Mean totals by strategy and judge ===")
    print(df.groupby("strategy")[["gemini_total", "llama_total"]].mean().round(2))

    #Paired Wilcoxon signed-rank: tests whether few-shot consistently
    #beats zero-shot across concepts
    print("\n=== Paired Wilcoxon (few_shot vs zero_shot) per judge ===")
    for judge_col in ["gemini_total", "llama_total"]:
        zs = df[df.strategy == "zero_shot"].sort_values("concept")[judge_col].values
        fs = df[df.strategy == "few_shot"].sort_values("concept")[judge_col].values
        try:
            stat, pval = wilcoxon(fs, zs)
            print(f"  {judge_col}: W={stat:.1f}  p={pval:.4f}  "
                  f"mean diff fs-zs={fs.mean()-zs.mean():+.2f}")
        except ValueError as e:
            print(f"  {judge_col}: test failed ({e})")

    #Spearman rank correlation measures whether the judges agree on which buildings are good,
    #independent of whether they agree on the prompting strategy
    print("\n=== Inter-rater agreement (Spearman) ===")
    rho, p = spearmanr(df.gemini_total, df.llama_total)
    print(f"  rho={rho:.3f}  p={p:.4f}  (across {len(df)} ratings)")

if __name__ == "__main__":
    main()