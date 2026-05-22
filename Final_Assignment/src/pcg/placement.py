"""
Terrain-aware placement helpers.

Reads the world heightmap to determine where the ground actually is and
whether a given footprint is buildable (not too sloped, not in water).
"""
from typing import Optional, Tuple
from gdpc import Editor
from gdpc.vector_tools import ivec3, ivec2, Rect


def load_heightmap(editor: Editor, area_box):
    """Load a heightmap covering the build area. Returns (heightmap, rect)."""
    rect = Rect(
        offset=ivec2(area_box.offset.x, area_box.offset.z),
        size=ivec2(area_box.size.x, area_box.size.z),
    )
    world_slice = editor.loadWorldSlice(rect)
    heightmap = world_slice.heightmaps["MOTION_BLOCKING_NO_LEAVES"]
    return heightmap, rect


def evaluate_footprint(heightmap, rect: Rect, x: int, z: int, w: int, d: int) -> Optional[Tuple[int, int]]:
    """
    Evaluate a building footprint at world (x, z) of size w x d.

    Returns (ground_y, fill_below) if buildable, or None if the position is
    out of bounds or too sloped.
    """
    heights = []
    for ix in range(w):
        for iz in range(d):
            lx = (x + ix) - rect.offset.x
            lz = (z + iz) - rect.offset.y  # Rect uses xy attributes for xz coords
            if lx < 0 or lx >= rect.size.x or lz < 0 or lz >= rect.size.y:
                return None
            heights.append(int(heightmap[lx][lz]))
    slope = max(heights) - min(heights)
    if slope > 5:
        return None  # too steep, skip this spot
    ground_y = max(heights) - 1   # top solid block at highest point
    fill_below = slope + 1        # bury foundation down to the lowest point
    return ground_y, fill_below


def is_water_at(editor: Editor, x: int, y: int, z: int) -> bool:
    """Crude water check by sampling one block."""
    block = editor.getBlock(ivec3(x, y, z))
    name = str(block).lower()
    return "water" in name or "lava" in name