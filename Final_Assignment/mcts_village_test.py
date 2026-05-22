"""Plan a village layout with MCTS, then build it on the island."""
import random
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3

from src.pcg.generator import GreekIslandBuilder
from src.pcg.placement import load_heightmap, evaluate_footprint, is_water_at
from src.pcg.details import draw_path, place_well, place_tree, write_text_on_ground
from src.pcg.configs import random_house, chapel, small_church
from src.mcts.planner import (
    get_candidate_positions, mcts_search, random_layout, score_layout,
    CHAPEL, CHURCH, HOUSE,
)


def build_placements(editor, builder, placements, rng):
    """Realize an MCTS-planned layout in Minecraft. Returns annotated info per building."""
    placed_info = []
    for x, z, btype, planned_gy in placements:
        if btype == CHAPEL:
            params = chapel(rng)
        elif btype == CHURCH:
            params = small_church(rng)
        else:
            params = random_house(rng)
        w, d = params.footprint.width, params.footprint.depth
        # Use the planned ground level; fill below = 2 (generous foundation)
        origin = ivec3(x, planned_gy + 1, z)
        builder.build(params, origin, fill_below=2)
        placed_info.append({"label": btype, "x": x, "z": z, "w": w, "d": d, "gy": planned_gy})
    return placed_info


def main():
    seed = 42
    rng = random.Random(seed)
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    print(f"Build area: {build_area}")

    heightmap, rect = load_heightmap(editor, build_area)

    print("Computing candidate positions on the island...")
    candidates = get_candidate_positions(heightmap, rect, build_area)
    print(f"  {len(candidates)} buildable positions found.")

    if len(candidates) < 12:
        print(f"  Not enough positions ({len(candidates)} < 12). Try a larger build area.")
        return

    print("\nRunning MCTS (500 iterations)...")
    mcts_placements = mcts_search(candidates, target_size=12, iterations=500, seed=seed)
    mcts_score = score_layout(mcts_placements)

    print("Computing random baseline for comparison...")
    rand_placements = random_layout(candidates, target_size=12, seed=seed)
    rand_score = score_layout(rand_placements)

    improvement = (mcts_score - rand_score) / max(rand_score, 1e-6) * 100
    print(f"\n  Random baseline score: {rand_score:.3f}")
    print(f"  MCTS layout score:     {mcts_score:.3f}")
    print(f"  Improvement:           {improvement:+.1f}%")

    print(f"\n  MCTS placed: {len(mcts_placements)} buildings")
    print(f"  Building types: {[p[2] for p in mcts_placements]}")

    print("\nBuilding MCTS-planned village in Minecraft...")
    builder = GreekIslandBuilder(editor)
    placed = build_placements(editor, builder, mcts_placements, rng)
    editor.flushBuffer()

    # Reload heightmap for paths/details
    heightmap, rect = load_heightmap(editor, build_area)

    chapel_info = next((p for p in placed if p["label"] == CHAPEL), None)
    if chapel_info:
        cx = chapel_info["x"] + chapel_info["w"] // 2
        cz = chapel_info["z"] - 1
        print("Drawing roads to chapel...")
        for p in placed:
            if p["label"] == CHAPEL:
                continue
            bx = p["x"] + p["w"] // 2
            bz = p["z"] - 1
            draw_path(editor, heightmap, rect, (bx, bz), (cx, cz))

        well_x = cx + 5
        well_z = chapel_info["z"] + chapel_info["d"] // 2
        lx, lz = well_x - rect.offset.x, well_z - rect.offset.y
        if 0 <= lx < rect.size.x and 0 <= lz < rect.size.y:
            well_y = int(heightmap[lx][lz]) - 1
            print("Placing well...")
            place_well(editor, ivec3(well_x, well_y, well_z))

    print("Placing trees...")
    trees_placed = 0
    for _ in range(80):
        if trees_placed >= 10:
            break
        x = rng.randint(build_area.offset.x + 4, build_area.offset.x + build_area.size.x - 5)
        z = rng.randint(build_area.offset.z + 4, build_area.offset.z + build_area.size.z - 5)
        too_close = any(
            p["x"] - 3 <= x <= p["x"] + p["w"] + 3 and p["z"] - 3 <= z <= p["z"] + p["d"] + 3
            for p in placed
        )
        if too_close:
            continue
        lx, lz = x - rect.offset.x, z - rect.offset.y
        if not (0 <= lx < rect.size.x and 0 <= lz < rect.size.y):
            continue
        ground_y = int(heightmap[lx][lz]) - 1
        block_at = str(editor.getBlock(ivec3(x, ground_y, z))).lower()
        if "grass" not in block_at:
            continue
        place_tree(editor, ivec3(x, ground_y + 1, z), rng)
        trees_placed += 1
    print(f"  {trees_placed} trees placed.")

    print("Writing NAXOS sign...")
    sign_x = build_area.offset.x + 25
    sign_z = build_area.offset.z + build_area.size.z - 12
    write_text_on_ground(
        editor, "NAXOS", sign_x, sign_z, heightmap, rect,
        Block("minecraft:blue_concrete"),
    )

    editor.flushBuffer()
    print(f"\nMCTS village complete: {len(placed)} buildings, {trees_placed} trees, paths, well, sign.")
    print(f"  Final MCTS score: {mcts_score:.3f} (vs random: {rand_score:.3f})")


if __name__ == "__main__":
    main()