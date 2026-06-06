"""Greek-island village: denser buildings, stone paths, a central well, and trees"""
import random
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3

from src.pcg.generator import GreekIslandBuilder
from src.pcg.placement import load_heightmap, evaluate_footprint, is_water_at
from src.schema import (
    BuildingParams, Style, RoofType, Decoration, Palette, Footprint,
)
from src.pcg.details import draw_path, place_well, place_tree, write_text_on_ground
from src.pcg.details import draw_path, place_well, place_tree, write_text_on_ground, pave_village_area, place_harbor


WHITE_WALLS = ["minecraft:white_concrete", "minecraft:smooth_quartz", "minecraft:quartz_block"]
BLUE_WHITE_ROOFS = [
    "minecraft:blue_concrete", "minecraft:light_blue_concrete",
    "minecraft:smooth_quartz", "minecraft:white_concrete",
]
BLUE_TRIMS = [
    "minecraft:blue_terracotta", "minecraft:light_blue_terracotta",
    "minecraft:blue_concrete",
]
STONE_ACCENTS = ["minecraft:cobblestone", "minecraft:stone_bricks"]


def random_house(rng):
    return BuildingParams(
        style=rng.choice(list(Style)),
        floors=rng.choice([1, 2, 2]),
        roof_type=rng.choice([RoofType.FLAT, RoofType.FLAT, RoofType.FLAT, RoofType.TERRACED]),
        palette=Palette(
            wall=rng.choice(WHITE_WALLS),
            roof=rng.choice(BLUE_WHITE_ROOFS),
            accent=rng.choice(STONE_ACCENTS),
            trim=rng.choice(BLUE_TRIMS),
        ),
        footprint=Footprint(width=rng.randint(7, 10), depth=rng.randint(7, 9)),
        decorations=rng.sample(
            [Decoration.STONE_PATH, Decoration.FLOWER_POTS, Decoration.CHIMNEY, Decoration.PERGOLA],
            k=rng.randint(1, 3),
        ),
    )


def chapel(rng):
    return BuildingParams(
        style=Style.CYCLADIC, floors=1, roof_type=RoofType.DOMED,
        palette=Palette(
            wall="minecraft:white_concrete",
            roof=rng.choice(["minecraft:blue_concrete", "minecraft:light_blue_concrete"]),
            accent="minecraft:cobblestone", trim="minecraft:blue_terracotta",
        ),
        footprint=Footprint(width=7, depth=7),
        decorations=[Decoration.STONE_PATH, Decoration.BELL_TOWER],
    )


def small_church(rng):
    return BuildingParams(
        style=Style.CYCLADIC, floors=1, roof_type=RoofType.FLAT,
        palette=Palette(
            wall="minecraft:white_concrete", roof="minecraft:smooth_quartz",
            accent="minecraft:white_terracotta", trim="minecraft:white_concrete",
        ),
        footprint=Footprint(width=5, depth=7),
        decorations=[Decoration.STONE_PATH, Decoration.CROSS],
    )


def main():
    seed = 42
    rng = random.Random(seed)
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    print(f"Build area: {build_area}")

    heightmap, rect = load_heightmap(editor, build_area)
    builder = GreekIslandBuilder(editor)

    grid_n = 4
    spacing = 14
    start_x = build_area.offset.x + 8
    start_z = build_area.offset.z + 8

    placed = []
    print("\nPlacing buildings...")
    for i in range(grid_n):
        for j in range(grid_n):
            x = start_x + i * spacing
            z = start_z + j * spacing
            if i == 1 and j == 1:
                params, label = chapel(rng), "chapel"
            elif i == 0 and j == 0:
                params, label = small_church(rng), "church"
            else:
                params, label = random_house(rng), "house"

            w, d = params.footprint.width, params.footprint.depth
            result = evaluate_footprint(heightmap, rect, x, z, w, d)
            if result is None:
                continue
            ground_y, fill_below = result
            if is_water_at(editor, x, ground_y, z):
                continue

            origin = ivec3(x, ground_y + 1, z)
            builder.build(params, origin, fill_below=fill_below)
            placed.append({"label": label, "x": x, "z": z, "w": w, "d": d, "gy": ground_y})

    print(f"  {len(placed)} buildings placed.")
    editor.flushBuffer()

    #Reload heightmap so paths/trees see the latest terrain
    heightmap, rect = load_heightmap(editor, build_area)

    chapel_info = next((p for p in placed if p["label"] == "chapel"), None)
    if chapel_info:
        chapel_x = chapel_info["x"] + chapel_info["w"] // 2
        chapel_z = chapel_info["z"] - 1

        print("Drawing stone paths to the chapel...")
        for p in placed:
            if p["label"] == "chapel":
                continue
            bx = p["x"] + p["w"] // 2
            bz = p["z"] - 1
            draw_path(editor, heightmap, rect, (bx, bz), (chapel_x, chapel_z))

        #Well near the chapel
        well_x = chapel_x + 5
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

    #Harbor at the coastline
    print("Building harbor...")
    place_harbor(editor, heightmap, rect, build_area)

    editor.flushBuffer()
    print(f"\nVillage complete: {len(placed)} buildings, {trees_placed} trees, paths and well.")


if __name__ == "__main__":
    main()