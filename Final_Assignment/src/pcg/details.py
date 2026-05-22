"""Small details for the village: stone paths, oak trees, and a central well."""
import random
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3


PATH_BLOCK = Block("minecraft:cobblestone")
WELL_RING = Block("minecraft:cobblestone")
WATER = Block("minecraft:water")
TREE_LOG = Block("minecraft:oak_log")
TREE_LEAVES = Block("minecraft:oak_leaves")


def draw_path(editor: Editor, heightmap, rect, start, end):
    """Draw a stone path from start (x,z) to end (x,z), following terrain height.
    Only replaces natural ground (grass/sand/dirt) — won't damage building walls."""
    x0, z0 = start
    x1, z1 = end

    dx = abs(x1 - x0)
    dz = abs(z1 - z0)
    sx = 1 if x0 < x1 else -1
    sz = 1 if z0 < z1 else -1
    err = dx - dz

    x, z = x0, z0
    safety = 400
    while safety > 0:
        safety -= 1
        lx, lz = x - rect.offset.x, z - rect.offset.y
        if 0 <= lx < rect.size.x and 0 <= lz < rect.size.y:
            ground_y = int(heightmap[lx][lz]) - 1
            current = str(editor.getBlock(ivec3(x, ground_y, z))).lower()
            if any(t in current for t in ["grass", "sand", "dirt"]):
                editor.placeBlock(ivec3(x, ground_y, z), PATH_BLOCK)
        if x == x1 and z == z1:
            break
        e2 = 2 * err
        if e2 > -dz:
            err -= dz
            x += sx
        if e2 < dx:
            err += dx
            z += sz


def place_well(editor: Editor, center: ivec3):
    """3x3 cobblestone ring with water in the middle and four corner pillars + roof beams."""
    # Ring (3x3 minus center)
    for dx in range(-1, 2):
        for dz in range(-1, 2):
            if (dx, dz) != (0, 0):
                editor.placeBlock(center + ivec3(dx, 0, dz), WELL_RING)
    # Water in center
    editor.placeBlock(center, WATER)
    # Corner pillars (2 blocks tall)
    for cdx, cdz in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
        editor.placeBlock(center + ivec3(cdx, 1, cdz), WELL_RING)
        editor.placeBlock(center + ivec3(cdx, 2, cdz), WELL_RING)
    # Roof beams across the top
    for cdx in [-1, 1]:
        for cdz in [-1, 0, 1]:
            editor.placeBlock(center + ivec3(cdx, 3, cdz), WELL_RING)


def place_tree(editor: Editor, base: ivec3, rng: random.Random):
    """Simple oak tree: 4-6 block trunk with a leafy crown on top."""
    height = rng.randint(4, 6)
    for y in range(height):
        editor.placeBlock(base + ivec3(0, y, 0), TREE_LOG)
    # Crown
    top = base + ivec3(0, height - 1, 0)
    for dy in range(0, 3):
        radius = 2 if dy < 2 else 1
        for dx in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                if (dx, dz) == (0, 0) and dy < 2:
                    continue
                if abs(dx) + abs(dz) <= radius + 1:
                    editor.placeBlock(top + ivec3(dx, dy, dz), TREE_LEAVES)
    editor.placeBlock(base + ivec3(0, height, 0), TREE_LEAVES)

# 5x5 block font for writing words
LETTERS = {
    'N': ['#...#', '##..#', '#.#.#', '#..##', '#...#'],
    'A': ['.###.', '#...#', '#####', '#...#', '#...#'],
    'X': ['#...#', '.#.#.', '..#..', '.#.#.', '#...#'],
    'O': ['.###.', '#...#', '#...#', '#...#', '.###.'],
    'S': ['.####', '#....', '.###.', '....#', '####.'],
}


def write_text_on_ground(editor: Editor, text: str, start_x: int, start_z: int,
                          heightmap, rect, block: Block,
                          char_width: int = 5, spacing: int = 1,
                          max_height_above_sea: int = 8):
    """Write text flat on the terrain. Each block is placed one above the local ground.
    Skips positions where the ground is too high (i.e. on building roofs)."""
    SEA_LEVEL = 63
    for i, char in enumerate(text.upper()):
        if char not in LETTERS:
            continue
        letter = LETTERS[char]
        offset_x = i * (char_width + spacing)
        for row, line in enumerate(letter):
            for col, c in enumerate(line):
                if c != '#':
                    continue
                x = start_x + offset_x + col
                z = start_z + row
                lx, lz = x - rect.offset.x, z - rect.offset.y
                if not (0 <= lx < rect.size.x and 0 <= lz < rect.size.y):
                    continue
                top_y = int(heightmap[lx][lz])
                # Skip if we're on top of a building
                if top_y - SEA_LEVEL > max_height_above_sea:
                    continue
                editor.placeBlock(ivec3(x, top_y, z), block)