# Greek Island Village Generator

An AI-driven procedural settlement generator for Minecraft, combining Procedural Content Generation (PCG), Monte Carlo Tree Search (MCTS), and Large Language Model (LLM) prompting into a single pipeline. Final assignment for the Modern Game AI course.

The system generates a Cycladic-style (Santorini / Mykonos) island village: an LLM converts natural-language building concepts into structured parameters, MCTS plans the village layout on procedurally-generated island terrain, and a parameter-driven PCG system constructs each building block-by-block via the GDPC interface.

## Architecture

The pipeline has four layers:

| Layer | Technique | Module |
|-------|-----------|--------|
| 0. Terrain | Simplex noise + radial falloff | `src/pcg/island.py` |
| 1. Building | Parameter-driven PCG | `src/pcg/generator.py` |
| 2. Semantics | LLM (Google Gemini 2.5 Flash) | `src/llm/client.py` |
| 3. Layout | MCTS (UCT) | `src/mcts/planner.py` |

## Requirements

- Python 3.11+
- Minecraft Java Edition 1.21.11 with Fabric loader
- Fabric API and the [GDMC HTTP Interface mod](https://github.com/Niels-NTG/gdmc_http_interface) v1.8.1
- API keys for Google Gemini and Groq (Llama judge for the LLM experiment)

## Setup

```bash
# Create a conda environment with Python 3.11
conda create -n village python=3.11 -y
conda activate village

# Install dependencies
pip install -r requirements.txt

# Create a .env file with your API keys (never commit this file)
echo "GEMINI_API_KEY=your-gemini-key" > .env
echo "GROQ_API_KEY=your-groq-key" >> .env
```

Get a free Gemini API key at https://aistudio.google.com/app/apikey.
Get a free Groq API key at https://console.groq.com.

## Running the Project in Minecraft

1. Launch Minecraft, open a Creative-mode world with cheats enabled.
2. Verify GDPC can talk to the game:
```bash
   python test_connection.py
```
3. Set a build area in the Minecraft chat (≥80×80 recommended):
```
   /setbuildarea ~-40 ~-10 ~-40 ~40 ~30 ~40
```
4. Generate an island and a village:
```bash
   python island_test.py          # generates the Greek-island terrain
   python mcts_village_test.py    # plans and builds the village with MCTS
```

After the first successful island generation, the ocean location is cached at `data/island_location.json` for one-click reruns.

### Other Useful Scripts

- `python test_house.py` — build a single hardcoded Cycladic building
- `python village_test.py` — older grid-based village (random placement baseline)
- `python llm_village_test.py` — demo of LLM-driven building generation

## Reproducing the Experiments

All three experiments run on synthetic terrain — no Minecraft instance required for reproduction.

```bash
# Experiment 1: MCTS vs Random layout planning (30 seeds, ~5 min)
python experiments/exp_mcts_vs_random.py

# Experiment 2: LLM prompting strategy comparison (cached, ~1s; fresh run ~5 min)
python experiments/exp_llm_strategy.py
python rebuild_csv.py            # aggregates cached two-judge ratings

# Experiment 3: PCG sampler diversity analysis
python experiments/exp_pcg_variety.py
```

Results land in `results/` (CSV files) and `figures/` (PNGs). The LLM experiment uses cached responses from `data/llm_cache/`, so re-running is fast and free.

## Project Structure

```
Final_Assignment/
├── src/
│   ├── pcg/                    # Layer 0 + Layer 1: terrain and building PCG
│   ├── llm/                    # Layer 2: LLM client and prompts
│   └── mcts/                   # Layer 3: village layout planner
├── experiments/                # Three experiment scripts
├── data/llm_cache/             # Cached LLM responses (committed for reproducibility)
├── results/                    # Experiment output CSVs
├── figures/                    # Experiment figures (PNG)
├── test_*.py, *_test.py        # Manual test scripts
├── rebuild_csv.py              # Rebuilds the LLM CSV from cached judge files
├── requirements.txt
└── README.md
```

## Notes

- The `.env` file containing API keys must never be committed. It is listed in `.gitignore`.
- The LLM cache is committed so that experiment results are reproducible without consuming API quota.
- Build areas smaller than 80×80 may not produce enough buildable positions for the 12-building MCTS layout.

## Author

Michail Protonotarios — Final assignment, Modern Game AI course, June 2026.