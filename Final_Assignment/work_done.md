# Project Progress — Greek Island Village Generator

**Project:** AI-Driven Procedural Settlement Generation in Minecraft
**Theme:** Cycladic (Greek-island) village on a procedurally-generated island, named "NAXOS"
**Last updated:** May 15, 2026

## Status Summary

All three architectural layers from the proposal are implemented and working end-to-end. The pipeline goes:

**Concept text → LLM generates JSON parameters → MCTS plans village layout → PCG builds buildings on procedurally-generated island terrain.**

What's left: running the three experiments with statistics, and writing the LNCS paper.

## What's Working

### Layer 0 — Procedural Island Generation (added beyond the original proposal)

A self-contained terrain generator that creates a small Greek-island-style landmass in the build area. Uses radial falloff for the circular shape combined with Simplex noise for natural surface variation. Produces sandy beaches at the waterline, grass meadow on top, dirt and stone underneath. The generator is destructive — it overwrites whatever terrain was there, so the result is the same regardless of biome.

The ocean location is cached to disk after first run, so subsequent runs are fully automated: one command teleports the player, sets the build area, generates the island, and teleports the player above it.

### Layer 1 — Building PCG

`GreekIslandBuilder` class that consumes a `BuildingParams` schema and produces a single Cycladic building. Features:

- **Stacked, inset upper floors** producing rooftop terraces (the iconic Santorini stepped look)
- **Blue terracotta trim** around doors and windows (the iconic blue-on-white accent)
- **Exterior staircase** running up the back wall to the rooftop terrace
- **Four roof types**: flat with parapet, domed (chapels), gabled (traditional), terraced (hillside)
- **Seven decorations**: chimney, pergola, stone path, flower pots, bell tower, shutters, cross
- **Terrain-aware foundation** that extends down to bury into uneven ground

### Layer 2 — LLM Parameter Generation

`BuildingLLM` client using Google Gemini 2.5 Flash (free tier) to convert text concepts like "blue-domed chapel" or "Mykonos seaside cottage" into validated `BuildingParams` JSON.

- **Two prompting strategies**: zero-shot (instructions + concept) and few-shot (+ 3 examples)
- **Pydantic validation** on LLM output
- **Self-correcting retry loop**: on validation failure, the error is appended to the prompt and Gemini retries (up to 3 times)
- **Disk caching** at `data/llm_cache/`: every concept × strategy combination is saved as JSON, so repeated experiments are instant and free

Tested with 5 building concepts, all generated valid parameters on the first try.

### Layer 3 — MCTS Village Planner

`MCTSVillagePlanner` using UCT-based MCTS to search the space of building placements on the generated island.

- **State**: list of placed buildings (position, type, ground_y)
- **Actions**: place next building at one of ~120 candidate positions on the island
- **Scoring function** (weighted sum, range [0, 1]):
  - Flatness (20%): low variance in building ground levels
  - Spacing (40%): pairwise distances in the [12, 25] block sweet spot
  - Variety (20%): chapel + church + houses all present
  - Connectivity (20%): all buildings within 25 blocks of at least one other
- **500 iterations** by default
- **Random baseline** for comparison

**Result so far** (single seed, single island): MCTS produced a layout scoring **0.571** versus the random baseline's **0.469** — a **+21.8% improvement**. Multi-seed experiment with statistics is the next step.

### Village Details

Beyond the buildings themselves, the village also includes:

- **Cobblestone paths** drawn from each building's front door to the chapel (Bresenham line-stepping, only replacing natural ground so it won't damage buildings)
- **A central well** next to the chapel: 3×3 cobblestone ring with water in the middle and corner pillars
- **Scattered oak trees** in empty grass spots
- **"NAXOS" sign** spelled out in blue concrete blocks along the southern beach using a custom 5×5 block letter font

## Project Structure
Final_Assignment/
├── src/
│   ├── schema.py                  # BuildingParams pydantic schema + constraints
│   ├── pcg/
│   │   ├── generator.py           # GreekIslandBuilder (Layer 1)
│   │   ├── island.py              # Procedural island generator (Layer 0)
│   │   ├── placement.py           # Terrain heightmap helpers
│   │   ├── details.py             # Paths, well, trees, block-letter font
│   │   └── configs.py             # Shared building config functions
│   ├── llm/
│   │   ├── prompts.py             # Zero-shot and few-shot prompt templates
│   │   ├── client.py              # BuildingLLM (Layer 2)
│   │   └── test_connection.py     # Gemini API smoke test
│   └── mcts/
│       └── planner.py             # MCTSNode, mcts_search, scoring (Layer3)
├── data/
│   ├── llm_cache/                 # Saved LLM responses (one JSON per concept)
│   └── island_location.json       # Cached ocean coordinates for one-click reruns
├── test_connection.py             # GDPC ↔ Minecraft bridge test
├── test_house.py                  # Single hardcoded building test
├── island_test.py                 # Generate island + auto-teleport
├── village_test.py                # Grid-placed village + paths + trees +NAXOS sign
├── llm_village_test.py            # LLM-generated buildings demo
├── mcts_village_test.py           # MCTS-planned village (current main pipeline)
├── requirements.txt
├── .env                           # GEMINI_API_KEY (gitignored)
└── .gitignore

## How to Run

### Setup (one time)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
# Create .env file with: GEMINI_API_KEY=AIza...your-key...
```

You also need Minecraft 1.21.11 with the Fabric loader, Fabric API, and the GDMC HTTP Interface mod installed.

### Setting up the world (first time)

1. Launch Minecraft and join a world with cheats enabled (Creative mode)
2. In Minecraft chat:
   - `/locate biome minecraft:ocean` — find ocean and click the coords to teleport
   - `/setbuildarea ~-40 ~-10 ~-40 ~40 ~30 ~40` — define an 80×80 area
   - Optionally `/setworldspawn` so you always start here

### Generating a full village

```bash
python island_test.py          # generates the island, teleports above
python mcts_village_test.py    # plans + builds the village with MCTS
```

After the first successful run, the ocean location is cached. From then on, `python island_test.py` alone fully regenerates the island automatically — no chat commands needed.

### Other useful scripts

- `python test_connection.py` — verify Python↔Minecraft bridge
- `python -m src.llm.test_connection` — verify Gemini API
- `python village_test.py` — older grid-based version (random/baseline placement)
- `python llm_village_test.py` — demo of LLM-driven building generation

## Tech Stack

- **Python 3.11** with venv
- **GDPC 8.1.0** (Minecraft block placement library)
- **GDMC HTTP Interface mod 1.8.1** (Fabric mod for Minecraft 1.21.11)
- **pydantic 2.x** (schema validation for LLM output)
- **google-genai** (Gemini API SDK)
- **opensimplex** (Simplex noise for island terrain)
- **numpy** (heightmap arrays and statistics)

## Lecture Connections

The proposal mentioned three lecture connections; here's how the implementation maps to each:

- **PCG lecture**: building generator with parameter schema (Layer 1), procedural island terrain (Layer 0)
- **Search / MCTS lecture**: UCT-based village layout planner with custom rollout and scoring (Layer 3)
- **LLMs / Deep Learning lecture**: prompt engineering, zero-shot vs few-shot strategies, structured JSON output, schema-driven validation (Layer 2)
- **Experimentation lecture**: baselines, controlled comparisons, metric design (the upcoming experiments)

## Results So Far

| Metric | Random Baseline | MCTS-500 | Improvement |
|--------|:---:|:---:|:---:|
| Layout score (single seed) | 0.469 | 0.571 | +21.8% |

Multi-seed experiment with proper statistics still to come.

## What's Left

### Experiments (~1.5 days)

1. **MCTS vs Random** — 30 seeds × 4 conditions (random, MCTS-100, MCTS-500, MCTS-1000). Compute mean ± std and paired Wilcoxon test. Plot iteration curve.
2. **LLM strategy comparison** — 5 building concepts × 2 strategies (zero-shot, few-shot). Rate each output 1–5 on semantic coherence; LLM-as-judge as a second rater. Report Spearman correlation between raters.
3. **PCG variety analysis** — Generate 12 LLM building configs and compute diversity metrics: roof type entropy, palette uniqueness, footprint variance.

### Paper (~3 days)

LNCS template, target 14–16 pages. Sections planned:

- Introduction & motivation (GDMC competition framing)
- Related work (PCG, MCTS in level design, LLMs for structured output)
- System architecture (three-layer diagram)
- Layer-by-layer implementation
- Three experiment sections
- Lecture connections
- Gen AI usage disclosure
- Limitations and conclusion

### Code cleanup & submission (~1 day)

- Single `run.py` entry point with `--mode` flag
- README with one-paragraph setup + run commands
- Pinned `requirements.txt`
- Zip everything and submit to Brightspace before May 29 deadline

## Gen AI Usage So Far

Used Claude (Anthropic) throughout as a coding assistant and architectural sounding board. Specifically:

- Initial architecture design and scoping (which features to prioritize given solo timeline)
- Iterative code review and debugging
- Prompt engineering for Gemini (the few-shot examples)
- Designing the MCTS scoring function

All code is reviewed before commit; Gemini is used only as the LLM in Layer 2 (Anthropic API was not used in the project pipeline).

## Notes for Teammates

- The cached ocean location lives at `data/island_location.json` — delete it to pick a new spawn spot
- The LLM cache at `data/llm_cache/` is committed-able if you want to share generated outputs; it's currently gitignored
- The build area must be at least 80×80 for the 12-building MCTS to find enough valid positions
- If `find_ocean` returns "not found" in any script, you need to manually `/locate biome minecraft:ocean` once