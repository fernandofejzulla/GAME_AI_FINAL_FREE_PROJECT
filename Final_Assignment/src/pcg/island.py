"""
Procedural island generator (Layer 0: terrain PCG).

Generates a small Greek-island-style landmass in the build area, replacing
any existing terrain with water and a freshly-generated island.
"""
import math
import numpy as np
from opensimplex import OpenSimplex
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3


SEA_LEVEL = 63
MAX_ISLAND_HEIGHT = 12
EDGE_MARGIN = 4
NOISE_SCALE = 18
NOISE_AMPLITUDE = 4
BEACH_THRESHOLD = 1
CLEAR_HEADROOM = 15   # clear this many blocks above max possible island top


def generate_island(editor: Editor, build_area, seed: int = 42) -> np.ndarray:
    """
    Generate an island in the build area, overwriting any existing terrain.

    Returns the absolute heightmap (world Y of top block at each (x, z)).
    """
    w = build_area.size.x
    d = build_area.size.z
    cx = w / 2
    cz = d / 2
    max_radius = min(w, d) / 2 - EDGE_MARGIN

    noise = OpenSimplex(seed=seed)

    rel_heights = np.zeros((w, d), dtype=int)
    for x in range(w):
        for z in range(d):
            dist = math.sqrt((x - cx) ** 2 + (z - cz) ** 2) / max_radius
            falloff = max(0.0, 1.0 - dist ** 2)
            n = noise.noise2(x / NOISE_SCALE, z / NOISE_SCALE)
            h = falloff * MAX_ISLAND_HEIGHT + n * NOISE_AMPLITUDE
            rel_heights[x][z] = max(0, int(round(h)))

    AIR = Block("minecraft:air")
    WATER = Block("minecraft:water")
    SAND = Block("minecraft:sand")
    GRASS = Block("minecraft:grass_block")
    DIRT = Block("minecraft:dirt")
    STONE = Block("minecraft:stone")

    clear_top_y = SEA_LEVEL + MAX_ISLAND_HEIGHT + CLEAR_HEADROOM
    clear_bottom_y = SEA_LEVEL - 5

    land_count = int((rel_heights > 0).sum())
    print(f"Placing island: {land_count} land columns of {w * d} total...")
    print(f"Clearing existing terrain in build area...")

    for x in range(w):
        for z in range(d):
            h = int(rel_heights[x][z])
            wx = build_area.offset.x + x
            wz = build_area.offset.z + z

            if h <= 0:
                # Ocean column: stone seabed → water → air, replacing whatever was here
                for y in range(clear_bottom_y, SEA_LEVEL):
                    editor.placeBlock(ivec3(wx, y, wz), WATER)
                editor.placeBlock(ivec3(wx, SEA_LEVEL, wz), WATER)
                for y in range(SEA_LEVEL + 1, clear_top_y):
                    editor.placeBlock(ivec3(wx, y, wz), AIR)
            else:
                # Island column: stack of stone → dirt/sand → grass/sand
                top_y = SEA_LEVEL + h
                is_beach = h <= BEACH_THRESHOLD
                for y in range(clear_bottom_y, top_y + 1):
                    if y == top_y:
                        block = SAND if is_beach else GRASS
                    elif y >= top_y - 2:
                        block = SAND if is_beach else DIRT
                    else:
                        block = STONE
                    editor.placeBlock(ivec3(wx, y, wz), block)
                # Air above the island
                for y in range(top_y + 1, clear_top_y):
                    editor.placeBlock(ivec3(wx, y, wz), AIR)

    abs_heights = SEA_LEVEL + rel_heights
    abs_heights[rel_heights == 0] = SEA_LEVEL
    return abs_heights