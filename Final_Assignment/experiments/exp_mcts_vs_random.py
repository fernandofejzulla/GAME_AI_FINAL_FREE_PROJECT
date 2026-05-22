"""
Experiment 1: MCTS vs Random village layout planner.

For each of N seeds, generate a synthetic island heightmap and run four conditions:
random baseline, MCTS-100, MCTS-500, MCTS-1000.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import csv
import math
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from opensimplex import OpenSimplex
from scipy import stats as scipy_stats

from src.mcts.planner import (
    get_candidate_positions, mcts_search, random_layout, score_layout,
)


# matches the islands actually built in Minecraft.
SEA_LEVEL = 63
MAX_ISLAND_HEIGHT = 12
EDGE_MARGIN = 4
NOISE_SCALE = 18
NOISE_AMPLITUDE = 4
BUILD_AREA_SIZE = 80
TARGET_BUILDINGS = 12
N_SEEDS = 30


# Minimal mocks so we can call get_candidate_positions without Minecraft.
class _Coord:
    """Exposes both .x/.y (Rect convention) and .x/.z (BuildArea convention)."""
    def __init__(self, a, b):
        self.x = a
        self.y = b
        self.z = b


class _MockRect:
    def __init__(self, ox, oz, sx, sz):
        self.offset = _Coord(ox, oz)
        self.size = _Coord(sx, sz)


class _MockBuildArea:
    def __init__(self, x, z, w, d):
        self.offset = _Coord(x, z)
        self.size = _Coord(w, d)


def compute_island_heightmap(width: int, depth: int, seed: int) -> np.ndarray:
    """Generate a synthetic island heightmap using the same algorithm as src/pcg/island.py.
    Returns absolute Y of the first AIR block above ground at each (x, z)."""
    cx, cz = width / 2, depth / 2
    max_radius = min(width, depth) / 2 - EDGE_MARGIN
    noise = OpenSimplex(seed=seed)

    rel = np.zeros((width, depth), dtype=int)
    for x in range(width):
        for z in range(depth):
            dist = math.sqrt((x - cx) ** 2 + (z - cz) ** 2) / max_radius
            falloff = max(0.0, 1.0 - dist ** 2)
            n = noise.noise2(x / NOISE_SCALE, z / NOISE_SCALE)
            h = falloff * MAX_ISLAND_HEIGHT + n * NOISE_AMPLITUDE
            rel[x][z] = max(0, int(round(h)))

    abs_h = SEA_LEVEL + rel
    abs_h[rel == 0] = SEA_LEVEL
    return abs_h + 1  # GDPC convention: Y of first air block above the surface


def run_single_seed(seed: int) -> dict:
    """Run all four conditions on one synthetic island. Returns score per condition."""
    heightmap = compute_island_heightmap(BUILD_AREA_SIZE, BUILD_AREA_SIZE, seed)
    rect = _MockRect(0, 0, BUILD_AREA_SIZE, BUILD_AREA_SIZE)
    build_area = _MockBuildArea(0, 0, BUILD_AREA_SIZE, BUILD_AREA_SIZE)

    candidates = get_candidate_positions(heightmap, rect, build_area)
    if len(candidates) < TARGET_BUILDINGS:
        return None

    scores = {}
    scores['random'] = score_layout(random_layout(candidates, TARGET_BUILDINGS, seed))
    scores['mcts_100'] = score_layout(mcts_search(candidates, TARGET_BUILDINGS, 100, seed))
    scores['mcts_500'] = score_layout(mcts_search(candidates, TARGET_BUILDINGS, 500, seed))
    scores['mcts_1000'] = score_layout(mcts_search(candidates, TARGET_BUILDINGS, 1000, seed))
    return scores


def main():
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)
    figures_dir = Path("figures")
    figures_dir.mkdir(exist_ok=True)

    print(f"Running {N_SEEDS} seeds × 4 conditions...")
    all_scores = {c: [] for c in ['random', 'mcts_100', 'mcts_500', 'mcts_1000']}
    seeds_used = []

    for seed in range(N_SEEDS):
        print(f"  seed {seed:>2}: ", end="", flush=True)
        result = run_single_seed(seed)
        if result is None:
            print("skipped (not enough buildable positions)")
            continue
        for cond, s in result.items():
            all_scores[cond].append(s)
        seeds_used.append(seed)
        print(" ".join(f"{c}={result[c]:.3f}" for c in ['random', 'mcts_100', 'mcts_500', 'mcts_1000']))

    # ---- Save raw data ----
    csv_path = output_dir / "exp_mcts_vs_random.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["seed", "condition", "score"])
        for cond, scores in all_scores.items():
            for s_idx, score in enumerate(scores):
                writer.writerow([seeds_used[s_idx], cond, f"{score:.4f}"])
    print(f"\nSaved raw scores: {csv_path}")

    # ---- Summary stats ----
    print(f"\n{'Condition':<12} {'Mean':>8} {'Std':>8} {'Median':>8} {'N':>5}")
    print("-" * 45)
    for cond in ['random', 'mcts_100', 'mcts_500', 'mcts_1000']:
        scores = np.array(all_scores[cond])
        print(f"{cond:<12} {scores.mean():>8.3f} {scores.std():>8.3f} {np.median(scores):>8.3f} {len(scores):>5}")

    # ---- Paired Wilcoxon tests vs random ----
    print("\nPaired Wilcoxon signed-rank test (each MCTS condition vs random):")
    print(f"{'Condition':<12} {'Statistic':>10} {'p-value':>10} {'effect':>10}")
    print("-" * 45)
    random_arr = np.array(all_scores['random'])
    for cond in ['mcts_100', 'mcts_500', 'mcts_1000']:
        cond_arr = np.array(all_scores[cond])
        if len(cond_arr) != len(random_arr) or len(random_arr) == 0:
            print(f"{cond:<12}  (length mismatch)")
            continue
        try:
            stat, pval = scipy_stats.wilcoxon(cond_arr, random_arr)
            mean_diff = (cond_arr - random_arr).mean()
            print(f"{cond:<12} {stat:>10.2f} {pval:>10.5f} {mean_diff:>+10.3f}")
        except ValueError as e:
            print(f"{cond:<12}  (test failed: {e})")

    # ---- Iteration curve plot ----
    fig, ax = plt.subplots(figsize=(7, 4.5))
    x_vals = [0, 100, 500, 1000]
    means, stds = [], []
    for cond in ['random', 'mcts_100', 'mcts_500', 'mcts_1000']:
        scores = np.array(all_scores[cond])
        means.append(scores.mean())
        stds.append(scores.std())

    ax.errorbar(x_vals, means, yerr=stds, marker='o', markersize=8,
                capsize=5, linewidth=2, color="#496376")
    ax.axhline(means[0], color='gray', linestyle='--', alpha=0.5, label='random baseline')
    ax.set_xlabel('MCTS iterations')
    ax.set_ylabel('Village layout score')
    ax.set_title(f'MCTS vs Random ({len(seeds_used)} seeds, mean ± std)')
    ax.grid(alpha=0.3)
    ax.legend()
    plt.tight_layout()
    fig_path = figures_dir / "fig_mcts_iteration_curve.png"
    plt.savefig(fig_path, dpi=130)
    print(f"\nSaved plot: {fig_path}")

    # ---- Per-seed paired comparison plot ----
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    seeds_x = np.arange(len(seeds_used))
    width = 0.2
    colors = ['#888888', '#aec7e8', '#1f77b4', '#08306b']
    for i, cond in enumerate(['random', 'mcts_100', 'mcts_500', 'mcts_1000']):
        ax2.bar(seeds_x + i * width, all_scores[cond], width, label=cond, color=colors[i])
    ax2.set_xlabel('Seed (sorted)')
    ax2.set_ylabel('Village layout score')
    ax2.set_title('Per-seed scores: random vs MCTS conditions')
    ax2.legend(ncol=4, fontsize=8)
    plt.tight_layout()
    fig2_path = figures_dir / "fig_mcts_per_seed.png"
    plt.savefig(fig2_path, dpi=130)
    print(f"Saved plot: {fig2_path}")


if __name__ == "__main__":
    main()