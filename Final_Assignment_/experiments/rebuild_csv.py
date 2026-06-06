"""Rebuild the experiment CSV from cached judge JSON files. No API calls."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from src.llm.client import BuildingLLM

# Same 18-concept list you used in exp_llm_strategy.py — must match exactly
CONCEPTS = [
    "fisherman's cottage by the sea, simple and weathered",
    "small Cycladic cottage with a flower-pot porch",
    "tiny one-room shepherd's hut on a hillside",
    "modest village house with a stone path and chimney",
    "wealthy merchant's two-story house with balcony and ornate trim",
    "two-story Mykonos seaside villa with pergola and rooftop terrace",
    "rustic farmer's house with stone accents and rooftop terrace",
    "spacious family home, white walls, blue shutters, gabled roof",
    "small whitewashed chapel with a prominent blue dome",
    "tiny clifftop chapel with a single cross",
    "blue-domed church with bell tower",
    "village chapel with stone foundation and white dome",
    "village tavern, welcoming with broad terrace and decorative trim",
    "small bakery with chimney and shuttered windows",
    "harbour-side fish market, single floor, simple and weathered",
    "blacksmith's workshop with stone walls and rooftop chimney",
    "tiny white watchtower overlooking the sea",
    "windmill-style building, tall and narrow, white with blue trim",
]

JUDGE_CACHE = Path("data/llm_cache/judge")

def cache_key(concept, strategy, params_dict):
    blob = f"{concept}|{strategy}|{json.dumps(params_dict, sort_keys=True)}"
    return hashlib.md5(blob.encode()).hexdigest()[:12]

def load_rating(judge_prefix, key):
    path = JUDGE_CACHE / f"{judge_prefix}{key}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())

llm = BuildingLLM()  # only reads cache, no API calls if all concepts cached
rows = []
missing = []

for concept in CONCEPTS:
    for strategy in ["zero_shot", "few_shot"]:
        try:
            params = llm.generate(concept, strategy=strategy)
            params_dict = params.model_dump()
        except Exception as e:
            missing.append((concept, strategy, f"LLM generation: {e}"))
            continue

        key = cache_key(concept, strategy, params_dict)
        gem = load_rating("", key)        # gemini cache files have no prefix
        lla = load_rating("llama_", key)

        if gem is None and lla is None:
            missing.append((concept, strategy, "no judge cache at all"))
            continue

        row = {"concept": concept, "strategy": strategy}
        if gem:
            row["gemini_concept_fit"] = gem["concept_fit"]
            row["gemini_cultural"] = gem["cultural_authenticity"]
            row["gemini_coherence"] = gem["architectural_coherence"]
            row["gemini_total"] = gem["concept_fit"] + gem["cultural_authenticity"] + gem["architectural_coherence"]
        if lla:
            row["llama_concept_fit"] = lla["concept_fit"]
            row["llama_cultural"] = lla["cultural_authenticity"]
            row["llama_coherence"] = lla["architectural_coherence"]
            row["llama_total"] = lla["concept_fit"] + lla["cultural_authenticity"] + lla["architectural_coherence"]
        rows.append(row)

df = pd.DataFrame(rows)
Path("results").mkdir(exist_ok=True)
df.to_csv("results/exp_llm_strategy.csv", index=False)

print(f"\nRebuilt CSV: {len(df)} rows ({df.gemini_total.notna().sum()} with Gemini, "
      f"{df.llama_total.notna().sum()} with Llama, "
      f"{(df.gemini_total.notna() & df.llama_total.notna()).sum()} with both)")
print(f"Saved to results/exp_llm_strategy.csv")

if missing:
    print(f"\n{len(missing)} (concept, strategy) pairs missing from cache:")
    for c, s, reason in missing:
        print(f"  [{s}] {c[:60]}: {reason}")

# Stats on pairs that have BOTH judges
print("\n=== Mean totals by strategy and judge (BOTH-judge subset) ===")
both = df.dropna(subset=["gemini_total", "llama_total"])
print(f"n with both judges = {len(both)}, concepts = {both.concept.nunique()}")
print(both.groupby("strategy")[["gemini_total", "llama_total"]].mean().round(2))

from scipy.stats import wilcoxon, spearmanr
print("\n=== Paired Wilcoxon (few_shot vs zero_shot) per judge ===")
for judge_col in ["gemini_total", "llama_total"]:
    paired = both.pivot_table(index="concept", columns="strategy", values=judge_col).dropna()
    if len(paired) < 2:
        print(f"  {judge_col}: only {len(paired)} paired concepts, skipping")
        continue
    zs = paired["zero_shot"].values
    fs = paired["few_shot"].values
    try:
        stat, pval = wilcoxon(fs, zs)
        print(f"  {judge_col}: n_pairs={len(paired)}, W={stat:.1f}, p={pval:.4f}, "
              f"mean diff fs-zs={fs.mean()-zs.mean():+.2f}")
    except ValueError as e:
        print(f"  {judge_col}: {e}")

print("\n=== Inter-rater agreement (Spearman) ===")
rho, p = spearmanr(both.gemini_total, both.llama_total)
print(f"  rho={rho:.3f}, p={p:.4f} (across {len(both)} ratings)")