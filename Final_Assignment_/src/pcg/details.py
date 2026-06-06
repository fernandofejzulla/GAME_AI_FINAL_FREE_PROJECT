"""Small details for the village: stone paths, oak trees, and a central well."""
import random
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3


PATH_BLOCK = Block("minecraft:smooth_quartz")    # was minecraft:cobblestone — white marble look
WELL_RING = Block("minecraft:cobblestone")
WATER = Block("minecraft:water")
TREE_LOG = Block("minecraft:oak_log")
TREE_LEAVES = Block("minecraft:oak_leaves")
PAVING = Block("minecraft:cobblestone")
DOCK_PLANK = Block("minecraft:spruce_planks")
DOCK_POST = Block("minecraft:spruce_log")
PLAZA_BLOCK = Block("minecraft:stone_bricks")    # for chapel plaza
BUILDING_PERIMETER = Block("minecraft:cobblestone")  # one-block ring around each house


def pave_village_area(editor, heightmap, rect, placements, padding: int = 2):
    """Paves a thin perimeter around each building and a plaza around the chapel.
    Leaves grass elsewhere so the village reads as buildings + paths + green."""
    natural = ("grass", "dirt", "sand", "podzol", "coarse_dirt")
    SEA_LEVEL = 63

    # Find chapel for the central plaza
    chapel_info = next((p for p in placements if p["label"] == "chapel"), None)

    def safe_pave(x, z, block):
        lx, lz = x - rect.offset.x, z - rect.offset.y
        if not (0 <= lx < rect.size.x and 0 <= lz < rect.size.y):
            return
        top_y = int(heightmap[lx][lz]) - 1
        if top_y <= SEA_LEVEL:  # would be over water — skip
            return
        current = str(editor.getBlock(ivec3(x, top_y, z))).lower()
        if any(t in current for t in natural):
            editor.placeBlock(ivec3(x, top_y, z), block)

    # Thin cobblestone perimeter around each building
    for p in placements:
        for x in range(p["x"] - padding, p["x"] + p["w"] + padding):
            for z in range(p["z"] - padding, p["z"] + p["d"] + padding):
                in_building = (p["x"] <= x < p["x"] + p["w"]
                               and p["z"] <= z < p["z"] + p["d"])
                if not in_building:
                    safe_pave(x, z, BUILDING_PERIMETER)

    # Stone-brick plaza around the chapel (4-block radius)
    if chapel_info:
        cx = chapel_info["x"] + chapel_info["w"] // 2
        cz = chapel_info["z"] + chapel_info["d"] // 2
        for x in range(cx - 6, cx + 7):
            for z in range(cz - 6, cz + 7):
                in_building = (chapel_info["x"] <= x < chapel_info["x"] + chapel_info["w"]
                               and chapel_info["z"] <= z < chapel_info["z"] + chapel_info["d"])
                if not in_building:
                    safe_pave(x, z, PLAZA_BLOCK)


def place_harbor(editor, heightmap, rect, build_area, sea_level: int = 63):
    """Build a LARGE port: 11x7 plaza, 3x12 dock, 7 lantern posts, 5 barrels, 3 boats."""
    print(f"  heightmap range: [{int(heightmap.min())}, {int(heightmap.max())}], sea_level={sea_level}")

    shore = []
    for x in range(5, rect.size.x - 8):
        for z in range(5, rect.size.y - 18):
            h = int(heightmap[x][z])
            if not (sea_level + 1 < h <= sea_level + 4):
                continue
            for dz in range(4, 10):
                if z + dz < rect.size.y and int(heightmap[x][z + dz]) <= sea_level + 1:
                    shore.append((x, z, h))
                    break

    if not shore:
        print("  WARNING: no shore candidates — harbor NOT placed")
        return None

    print(f"  found {len(shore)} shore candidates")
    shore.sort(key=lambda c: c[2])
    lx, lz, lh = shore[len(shore) // 4]
    wx = lx + rect.offset.x
    wz = lz + rect.offset.y
    base_y = lh - 1

    print(f"  building LARGE harbor at ({wx}, {base_y}, {wz})...")

    # 11x7 stone plaza on shore (was 5x3)
    for dx in range(-5, 6):
        for dz in range(-3, 4):
            editor.placeBlock(ivec3(wx + dx, base_y, wz + dz), PAVING)

    # Wide dock: 3 wide, 12 long (was 1 wide, 6 long)
    DOCK_HALF_W = 1
    DOCK_L = 12
    for dx in range(-DOCK_HALF_W, DOCK_HALF_W + 1):
        for d in range(1, DOCK_L + 1):
            editor.placeBlock(ivec3(wx + dx, base_y, wz + 3 + d), DOCK_PLANK)

    # Support posts beneath the dock (centered, every 4 blocks)
    for d in [4, 8, 12]:
        editor.placeBlock(ivec3(wx, base_y - 1, wz + 3 + d), DOCK_POST)
        editor.placeBlock(ivec3(wx, base_y - 2, wz + 3 + d), DOCK_POST)

    # 6 lantern posts in the water beside the dock (3 on each side)
    for side in [-2, 2]:
        for dz_offset in [4, 9, 13]:
            for y_offset in [-1, 0, 1]:
                editor.placeBlock(ivec3(wx + side, base_y + y_offset, wz + 3 + dz_offset), DOCK_POST)
            editor.placeBlock(ivec3(wx + side, base_y + 2, wz + 3 + dz_offset), Block("minecraft:lantern"))

    # Big lantern post at the very end of the dock
    end_z = wz + 3 + DOCK_L + 1
    for y_offset in [-1, 0, 1]:
        editor.placeBlock(ivec3(wx, base_y + y_offset, end_z), DOCK_POST)
    editor.placeBlock(ivec3(wx, base_y + 2, end_z), Block("minecraft:lantern"))

    # 5 barrels (fishing-supply decorations) on dock and plaza
    for bx, bz in [
        (wx, wz + 6), (wx + 1, wz + 10),
        (wx - 4, wz - 2), (wx + 4, wz - 2), (wx - 3, wz + 2),
    ]:
        editor.placeBlock(ivec3(bx, base_y + 1, bz), Block("minecraft:barrel"))

    editor.flushBuffer()

    # Two small fishing boats tied along the dock
    for bx, bz in [(wx - 3.5, wz + 7.5), (wx + 3.5, wz + 11.5)]:
        editor.runCommand(f"summon minecraft:oak_boat {bx} {base_y + 0.5} {bz}")

    # Big passenger ferry parked at the end of the dock, perpendicular to it
    ferry_z = end_z + 6  # 6 blocks beyond the end lantern
    place_passenger_ferry(editor, wx, ferry_z, sea_level)
    print(f"  ✓ passenger ferry placed at ({wx}, {sea_level}, {ferry_z})")

def place_passenger_ferry(editor, wx, wz, sea_level=63):
    """Build a Greek-island passenger ferry, ~18 blocks long, 5 wide.
    Centered at (wx, wz). Bow faces +x direction. Two decks, cabin, and smokestack."""
    HULL = Block("minecraft:white_concrete")
    BLUE = Block("minecraft:blue_concrete")
    DECK = Block("minecraft:spruce_planks")
    WINDOWS = Block("minecraft:glass")
    ROOF = Block("minecraft:light_blue_concrete")
    STACK = Block("minecraft:light_gray_concrete")
    RAILING = Block("minecraft:spruce_fence")

    LENGTH = 18
    WIDTH = 5
    HL = LENGTH // 2
    HW = WIDTH // 2
    base_y = sea_level

    # --- HULL (2 layers, white, with tapered bow on +x side) ---
    for dx in range(-HL, HL):
        for dz in range(-HW, HW + 1):
            bow_taper = max(0, dx - (HL - 3))
            if abs(dz) > HW - bow_taper:
                continue
            editor.placeBlock(ivec3(wx + dx, base_y - 1, wz + dz), HULL)
            editor.placeBlock(ivec3(wx + dx, base_y, wz + dz), HULL)

    # --- Blue gunwale stripe along both sides at deck level ---
    for dx in range(-HL, HL):
        bow_taper = max(0, dx - (HL - 3))
        side = HW - bow_taper
        if side >= 0:
            editor.placeBlock(ivec3(wx + dx, base_y + 1, wz - side), BLUE)
            editor.placeBlock(ivec3(wx + dx, base_y + 1, wz + side), BLUE)

    # --- Spruce deck floor ---
    for dx in range(-HL + 1, HL - 1):
        for dz in range(-HW + 1, HW):
            bow_taper = max(0, dx - (HL - 3))
            if abs(dz) > HW - 1 - bow_taper:
                continue
            editor.placeBlock(ivec3(wx + dx, base_y + 1, wz + dz), DECK)

    # --- Bridge / passenger cabin on the stern (back) ---
    cabin_x_back = -HL + 1
    cabin_l = 6
    cabin_x_front = cabin_x_back + cabin_l - 1
    cabin_w = HW - 1
    for dx in range(cabin_x_back, cabin_x_front + 1):
        for dz in range(-cabin_w, cabin_w + 1):
            for dy in range(2, 5):
                on_edge = (dx == cabin_x_back or dx == cabin_x_front
                           or dz == -cabin_w or dz == cabin_w)
                if on_edge:
                    block = WINDOWS if dy == 3 else HULL
                    editor.placeBlock(ivec3(wx + dx, base_y + dy, wz + dz), block)

    # Cabin roof
    for dx in range(cabin_x_back, cabin_x_front + 1):
        for dz in range(-cabin_w, cabin_w + 1):
            editor.placeBlock(ivec3(wx + dx, base_y + 5, wz + dz), ROOF)

    # --- Smokestack on cabin roof ---
    stack_x = cabin_x_front - 1
    for dy in range(6, 10):
        editor.placeBlock(ivec3(wx + stack_x, base_y + dy, wz), STACK)
    editor.placeBlock(ivec3(wx + stack_x, base_y + 10, wz), BLUE)

    # --- Railings on open deck (in front of cabin) and at the bow ---
    for dz in [-HW + 1, HW - 1]:
        for dx in range(cabin_x_front + 1, HL - 3):
            editor.placeBlock(ivec3(wx + dx, base_y + 2, wz + dz), RAILING)
    for dz in range(-HW + 2, HW - 1):
        editor.placeBlock(ivec3(wx + HL - 3, base_y + 2, wz + dz), RAILING)

    # Lanterns at the bridge corners
    for dz in [-cabin_w, cabin_w]:
        editor.placeBlock(ivec3(wx + cabin_x_front, base_y + 6, wz + dz),
                           Block("minecraft:lantern"))

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
            if ground_y < 64:        # ADD THIS: never draw paths over water
                continue
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