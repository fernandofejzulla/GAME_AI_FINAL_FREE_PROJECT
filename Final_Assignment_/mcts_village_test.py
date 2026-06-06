"""Plan a dense MCTS village with paved streets and a harbor."""
import random
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3

from src.pcg.generator import GreekIslandBuilder
from src.pcg.placement import load_heightmap
from src.pcg.details import draw_path, place_well, pave_village_area, place_harbor
from src.pcg.configs import random_house, chapel, small_church
from src.mcts.planner import (
    get_candidate_positions, mcts_search, random_layout, score_layout,
    CHAPEL, CHURCH, HOUSE,
)


def build_placements(editor, builder, placements, rng):
    """Realize an MCTS-planned layout, forcing the chapel into the most central position."""
    if not placements:
        return []

    # Compute centroid, then find the placement closest to it
    cx = sum(p[0] for p in placements) / len(placements)
    cz = sum(p[1] for p in placements) / len(placements)
    central_idx = min(
        range(len(placements)),
        key=lambda i: (placements[i][0] - cx) ** 2 + (placements[i][1] - cz) ** 2,
    )

    # Reassign building types: central = chapel, then church, then houses
    reordered = []
    for i, p in enumerate(placements):
        x, z, _, gy = p
        if i == central_idx:
            btype = CHAPEL
        elif i == 0 and central_idx != 0:
            btype = CHURCH
        elif i == 1 and central_idx != 1:
            btype = CHURCH if not any(pp[2] == CHURCH for pp in reordered) else HOUSE
        else:
            btype = HOUSE
        reordered.append((x, z, btype, gy))

    placed_info = []
    for x, z, btype, planned_gy in reordered:
        if btype == CHAPEL:
            params = chapel(rng)
        elif btype == CHURCH:
            params = small_church(rng)
        else:
            params = random_house(rng)
        w, d = params.footprint.width, params.footprint.depth
        builder.build(params, ivec3(x, planned_gy + 1, z), fill_below=2)
        placed_info.append({"label": btype, "x": x, "z": z, "w": w, "d": d, "gy": planned_gy})
    return placed_info

def main():
    seed = 42
    rng = random.Random(seed)
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    print(f"Build area: {build_area}")

    heightmap, rect = load_heightmap(editor, build_area)

    print("Computing candidate positions...")
    candidates = get_candidate_positions(heightmap, rect, build_area)
    print(f"  {len(candidates)} buildable positions found.")

    target = min(16, len(candidates))
    print(f"\nRunning MCTS (target={target}, 500 iterations)...")
    mcts_placements = mcts_search(candidates, target_size=target, iterations=500, seed=seed)
    mcts_score = score_layout(mcts_placements)
    rand_placements = random_layout(candidates, target_size=target, seed=seed)
    rand_score = score_layout(rand_placements)
    improvement = (mcts_score - rand_score) / max(rand_score, 1e-6) * 100
    print(f"  Random: {rand_score:.3f}   MCTS: {mcts_score:.3f}   ({improvement:+.1f}%)")

    print("\nBuilding village (chapel forced to centroid)...")
    builder = GreekIslandBuilder(editor)
    placed = build_placements(editor, builder, mcts_placements, rng)
    editor.flushBuffer()

    heightmap, rect = load_heightmap(editor, build_area)

    # Perimeter paving + chapel plaza
    print("Paving perimeters and chapel plaza...")
    pave_village_area(editor, heightmap, rect, placed, padding=2)
    editor.flushBuffer()

    heightmap, rect = load_heightmap(editor, build_area)

    # Paths to chapel — drawn AFTER paving so they cut through the green
    chapel_info = next((p for p in placed if p["label"] == CHAPEL), None)
    if chapel_info:
        cx_path = chapel_info["x"] + chapel_info["w"] // 2
        cz_path = chapel_info["z"] - 1
        print("Drawing paths from every building to chapel...")
        for p in placed:
            if p["label"] == CHAPEL:
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
    print(f"\nDone: {len(placed)} buildings, chapel at center, paths visible on grass.")

if __name__ == "__main__":
    main()