"""Compare zero-shot vs few-shot prompting for building parameter generation."""
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

from src.llm.client import BuildingLLM

load_dotenv()

CONCEPTS = [
    "fisherman's cottage by the sea, simple and weathered",
    "wealthy merchant's two-story house with balcony and ornate trim",
    "small whitewashed chapel with a prominent blue dome",
    "rustic farmer's house with stone accents and rooftop terrace",
    "village tavern, welcoming with broad terrace and decorative trim",
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

    # Try primary model, fall back to flash-lite if rate-limited
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


def main():
    llm = BuildingLLM()
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    rows = []
    for concept in CONCEPTS:
        for strategy in ["zero_shot", "few_shot"]:
            print(f"[{strategy}] generating: {concept[:55]}...")
            params = llm.generate(concept, strategy=strategy)
            params_dict = params.model_dump() if hasattr(params, "model_dump") else params

            print("  judging...")
            ratings = judge_one(client, concept, params_dict, strategy)

            rows.append({
                "concept": concept,
                "strategy": strategy,
                "concept_fit": ratings["concept_fit"],
                "cultural_authenticity": ratings["cultural_authenticity"],
                "architectural_coherence": ratings["architectural_coherence"],
                "total": ratings["concept_fit"] + ratings["cultural_authenticity"] + ratings["architectural_coherence"],
                "comment": ratings["comment"],
            })
            time.sleep(1.5)  # gentle rate limit

    Path("results").mkdir(exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv("results/exp_llm_strategy.csv", index=False)
    print(f"\nSaved: results/exp_llm_strategy.csv")

    print("\n=== Mean ratings by strategy ===")
    print(df.groupby("strategy")[
        ["concept_fit", "cultural_authenticity", "architectural_coherence", "total"]
    ].mean().round(2))

    zs = df[df.strategy == "zero_shot"].sort_values("concept")["total"].values
    fs = df[df.strategy == "few_shot"].sort_values("concept")["total"].values
    stat, pval = wilcoxon(fs, zs)
    print(f"\nWilcoxon signed-rank (few_shot vs zero_shot, total / 30):")
    print(f"  statistic={stat:.2f}  p-value={pval:.4f}")
    print(f"  mean diff (few_shot - zero_shot): {fs.mean() - zs.mean():+.2f} points")


if __name__ == "__main__":
    main()