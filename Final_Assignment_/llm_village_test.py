"""End-to-end demo: LLM generates building parameters, generator builds them.
Mirrors mcts_village_test.py: 12 buildings, central chapel, paved paths, harbor.
"""
import random

from gdpc import Editor
from gdpc.vector_tools import ivec3

from src.llm.client import BuildingLLM
from src.pcg.generator import GreekIslandBuilder
from src.pcg.placement import load_heightmap
from src.pcg.details import draw_path, place_well, pave_village_area, place_harbor
from src.mcts.planner import get_candidate_positions, is_too_close


# (concept, label) — label is used to identify the chapel for centering.
# Concepts deliberately steer the LLM toward Cycladic features (flat roofs,
# white walls, blue trim) and away from gabled/non-Greek styles.
# All concepts below are already cached from Experiment 2 — no API calls needed.
# Mix of residential, commercial, religious, and special buildings for maximum variety.
CONCEPTS = [
    # Religious — chapel goes centrally
    ("small whitewashed chapel with a prominent blue dome", "chapel"),
    ("blue-domed church with bell tower", "house"),
    ("tiny clifftop chapel with a single cross", "house"),
    ("village chapel with stone foundation and white dome", "house"),

    # Residential — simple cottages
    ("fisherman's cottage by the sea, simple and weathered", "house"),
    ("small Cycladic cottage with a flower-pot porch", "house"),
    ("tiny one-room shepherd's hut on a hillside", "house"),
    ("modest village house with a stone path and chimney", "house"),

    # Residential — larger houses
    ("wealthy merchant's two-story house with balcony and ornate trim", "house"),
    ("two-story Mykonos seaside villa with pergola and rooftop terrace", "house"),
    ("rustic farmer's house with stone accents and rooftop terrace", "house"),

    # Commercial / civic — different functions = different shapes
    ("village tavern, welcoming with broad terrace and decorative trim", "house"),
    ("small bakery with chimney and shuttered windows", "house"),
    ("harbour-side fish market, single floor, simple and weathered", "house"),
    ("blacksmith's workshop with stone walls and rooftop chimney", "house"),

    # Special / distinctive landmarks
    ("tiny white watchtower overlooking the sea", "house"),
    ("windmill-style building, tall and narrow, white with blue trim", "house"),
]

def main():
    random.seed(42)

    print("Generating building parameters via Gemini (few-shot strategy)...")
    llm = BuildingLLM()
    buildings = []
    for concept, label in CONCEPTS:
        print(f"  '{concept[:55]}'... ", end="", flush=True)
        params = llm.generate(concept, strategy="few_shot")
        print(f"OK ({params.style.value}/{params.roof_type.value}, "
              f"{params.footprint.width}x{params.footprint.depth})")
        buildings.append((concept, label, params))

    print("\nFinding valid island positions...")
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    heightmap, rect = load_heightmap(editor, build_area)
    builder = GreekIslandBuilder(editor)

    candidates = get_candidate_positions(heightmap, rect, build_area, step=6, footprint=9)
    print(f"Found {len(candidates)} valid positions on the island")

    random.shuffle(candidates)
    chosen = []
    for c in candidates:
        x, z, _, _ = c
        if not is_too_close(x, z, chosen, min_dist=9):
            chosen.append(c)
            if len(chosen) >= len(CONCEPTS):
                break
    print(f"Selected {len(chosen)} spread-out positions")

    if not chosen:
        print("No valid positions found!")
        return

    # Find the most geometrically central position and assign the chapel to it
    cx = sum(c[0] for c in chosen) / len(chosen)
    cz = sum(c[1] for c in chosen) / len(chosen)
    central_idx = min(
        range(len(chosen)),
        key=lambda i: (chosen[i][0] - cx) ** 2 + (chosen[i][1] - cz) ** 2,
    )

    chapel_buildings_idx = next(
        (i for i, (_, label, _) in enumerate(buildings) if label == "chapel"), 0
    )
    if central_idx != chapel_buildings_idx:
        buildings[chapel_buildings_idx], buildings[central_idx] = (
            buildings[central_idx], buildings[chapel_buildings_idx]
        )

    print("\nPlacing buildings (chapel at center)...")
    placed = []
    for i, (concept, label, params) in enumerate(buildings):
        if i >= len(chosen):
            print(f"  skip '{concept[:50]}': ran out of positions")
            continue
        x, z, ground_y, _ = chosen[i]
        origin = ivec3(x, ground_y + 1, z)
        print(f"  [{label}] {concept[:55]} at {origin}")
        builder.build(params, origin, fill_below=2)
        w, d = params.footprint.width, params.footprint.depth
        placed.append({"label": label, "x": x, "z": z, "w": w, "d": d, "gy": ground_y})

    editor.flushBuffer()
    heightmap, rect = load_heightmap(editor, build_area)

    print("Paving perimeters and chapel plaza...")
    pave_village_area(editor, heightmap, rect, placed, padding=2)
    editor.flushBuffer()

    heightmap, rect = load_heightmap(editor, build_area)

    chapel_info = next((p for p in placed if p["label"] == "chapel"), None)
    if chapel_info:
        cx_path = chapel_info["x"] + chapel_info["w"] // 2
        cz_path = chapel_info["z"] - 1
        print("Drawing paths from every building to chapel...")
        for p in placed:
            if p["label"] == "chapel":
                continue
            bx = p["x"] + p["w"] // 2
            bz = p["z"] - 1
            draw_path(editor, heightmap, rect, (bx, bz), (cx_path, cz_path))

        well_x = cx_path + 5
        well_z = chapel_info["z"] + chapel_info["d"] // 2
        lx, lz = well_x - rect.offset.x, well_z - rect.offset.y
        if 0 <= lx < rect.size.x and 0 <= lz < rect.size.y:
            well_y = int(heightmap[lx][lz]) - 1
            place_well(editor, ivec3(well_x, well_y, well_z))

    print("Building harbor...")
    place_harbor(editor, heightmap, rect, build_area)

    editor.flushBuffer()
    print(f"\nLLM village complete: {len(placed)} buildings + paved streets + harbor.")


if __name__ == "__main__":
    main()