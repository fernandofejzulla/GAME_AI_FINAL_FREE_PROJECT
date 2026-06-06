"""
Experiment 3: PCG variety analysis
"""
import math
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from src.pcg.configs import random_house, chapel, small_church

N_HOUSES = 40
N_CHAPELS = 10
N_CHURCHES = 10
SEED = 42


def shannon_entropy_bits(counts: Counter) -> float:
    """Returns 0 for empty input. Higher entropy = more uniform distribution
    across categories"""
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)


def main():
    rng = random.Random(SEED)
    n_total = N_HOUSES + N_CHAPELS + N_CHURCHES

    print(f"Generating {n_total} random BuildingParams "
          f"({N_HOUSES} houses + {N_CHAPELS} chapels + {N_CHURCHES} churches)...")
    
    #All three factories share the same seeded RNG, so the entire
    #60-sample corpus is deterministic and reproducible
    samples = []
    for _ in range(N_HOUSES):
        d = random_house(rng=rng).model_dump()
        d['_type'] = 'house'
        samples.append(d)
    for _ in range(N_CHAPELS):
        d = chapel(rng=rng).model_dump()
        d['_type'] = 'chapel'
        samples.append(d)
    for _ in range(N_CHURCHES):
        d = small_church(rng=rng).model_dump()
        d['_type'] = 'church'
        samples.append(d)

    #Flatten list-valued fields for CSV storage
    for d in samples:
        for k, v in d.items():
            if isinstance(v, list):
                d[k] = ', '.join(str(x) for x in v) if v else ''

    df = pd.DataFrame(samples)
    Path("results").mkdir(exist_ok=True)
    df.to_csv("results/exp_pcg_variety.csv", index=False)
    print(f"Saved: results/exp_pcg_variety.csv\n")
    print(f"Schema fields detected: {list(df.columns)}\n")

    
    #Categorical fields
    print("=== Categorical entropy (Shannon, bits) ===")
    for field in df.columns:
        if field == '_type' or pd.api.types.is_numeric_dtype(df[field]):
            continue
        series = df[field].astype(str)
        #Decorations is comma-joined split for true element entropy
        if field == 'decorations':
            vals = []
            for v in series:
                v = v.strip()
                if v:
                    vals.extend(s.strip() for s in v.split(',') if s.strip())
            counts = Counter(vals)
        else:
            counts = Counter(series)
        n_unique = len(counts)
        h = shannon_entropy_bits(counts)
        h_max = math.log2(n_unique) if n_unique > 1 else 1.0
        h_norm = h / h_max if h_max > 0 else 0
        print(f"  {field:25s} H = {h:.3f} bits "
              f"(max {h_max:.3f}, normalized {h_norm:.3f}, {n_unique} unique)")

    # ============ Numerical fields ============
    print("\n=== Numerical variance ===")
    num_fields = [c for c in df.columns if df[c].dtype in ('int64', 'float64')]
    for field in num_fields:
        col = df[field].dropna()
        if len(col) > 0:
            print(f"  {field:25s} mean={col.mean():6.2f}  std={col.std():5.2f}  "
                  f"range=[{col.min():g}, {col.max():g}]")

    #Combination uniqueness: how many distinct and combinations appear, low number means
    #the sampler revisits the same template variants
    print(f"\n=== Combinatorial uniqueness ===")
    for fieldset in [['style', 'roof_type'], ['style', 'roof_type', 'floors']]:
        keys = [c for c in fieldset if c in df.columns]
        if len(keys) >= 2:
            tuples = df[keys].astype(str).agg('|'.join, axis=1)
            n_unique = tuples.nunique()
            print(f"  {keys}: {n_unique} unique combinations in {n_total} samples "
                  f"({100*n_unique/n_total:.0f}% uniqueness ratio)")

    make_plot(df, n_total)


def make_plot(df, n_total):
    import ast
    Path("figures").mkdir(exist_ok=True)

    def parse_maybe_dict(x):
        if isinstance(x, dict):
            return x
        if x is None:
            return {}
        try:
            return ast.literal_eval(str(x))
        except (ValueError, SyntaxError):
            return {}

    def clean_label(x):
        s = str(x)
        return s.split('.')[-1] if '.' in s else s

    #Derive sub-fields from the dict columns
    if 'palette' in df.columns:
        df = df.copy()
        df['_roof_color'] = df['palette'].apply(
            lambda x: parse_maybe_dict(x).get('roof', '').replace('minecraft:', '')
        )
    if 'footprint' in df.columns:
        df['_width'] = df['footprint'].apply(lambda x: parse_maybe_dict(x).get('width'))
        df['_depth'] = df['footprint'].apply(lambda x: parse_maybe_dict(x).get('depth'))

    fig, axes = plt.subplots(2, 3, figsize=(13, 8), dpi=130)
    palette_colors = ['#0d3f7a', '#1f6feb', '#3b82f6', '#60a5fa', '#93c5fd', '#a9c5f0']

    #Top row: bars
    ax = axes[0, 0]
    counts = df['_type'].astype(str).value_counts().sort_index()
    ax.bar(range(len(counts)), counts.values, color=palette_colors[0], edgecolor='white')
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels([clean_label(x) for x in counts.index], fontsize=10)
    ax.set_title('Building type', fontweight='bold')
    ax.set_ylabel('Count')

    ax = axes[0, 1]
    counts = df['style'].astype(str).value_counts().sort_index()
    ax.bar(range(len(counts)), counts.values, color=palette_colors[1], edgecolor='white')
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels([clean_label(x) for x in counts.index], rotation=20, ha='right', fontsize=9)
    ax.set_title('Style', fontweight='bold')

    ax = axes[0, 2]
    counts = df['roof_type'].astype(str).value_counts().sort_index()
    ax.bar(range(len(counts)), counts.values, color=palette_colors[2], edgecolor='white')
    ax.set_xticks(range(len(counts)))
    ax.set_xticklabels([clean_label(x) for x in counts.index], rotation=20, ha='right', fontsize=9)
    ax.set_title('Roof type', fontweight='bold')

    #Bottom row: floors, footprint scatter, roof color
    ax = axes[1, 0]
    counts = df['floors'].value_counts().sort_index()
    ax.bar(counts.index, counts.values, color=palette_colors[3], edgecolor='white', width=0.5)
    ax.set_xticks(sorted(df['floors'].unique()))
    ax.set_title('Floors', fontweight='bold')
    ax.set_ylabel('Count')

    ax = axes[1, 1]
    if '_width' in df.columns and '_depth' in df.columns:
        rng = np.random.RandomState(0)
        wx = df['_width'].astype(float) + rng.normal(0, 0.08, len(df))
        wz = df['_depth'].astype(float) + rng.normal(0, 0.08, len(df))
        ax.scatter(wx, wz, alpha=0.55, s=70, color=palette_colors[4], edgecolor='white', linewidth=0.8)
        ax.set_xlabel('Width')
        ax.set_ylabel('Depth')
    ax.set_title('Footprint dimensions', fontweight='bold')

    ax = axes[1, 2]
    if '_roof_color' in df.columns:
        counts = df['_roof_color'].value_counts()
        ax.bar(range(len(counts)), counts.values, color=palette_colors[5], edgecolor='white')
        ax.set_xticks(range(len(counts)))
        ax.set_xticklabels(counts.index, rotation=20, ha='right', fontsize=9)
    ax.set_title('Roof color', fontweight='bold')

    for ax in axes.flatten():
        ax.grid(axis='y', alpha=0.25)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    plt.suptitle(f'PCG variety: distributions across {n_total} random building samples',
                 fontsize=13, fontweight='bold', y=1.00)
    plt.tight_layout()
    plt.savefig('figures/fig_pcg_variety.png', dpi=200, bbox_inches='tight')
    plt.close()
    print(f"\nSaved: figures/fig_pcg_variety.png")

if __name__ == "__main__":
    main()