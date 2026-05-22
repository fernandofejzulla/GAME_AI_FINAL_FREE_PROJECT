"""
Greek-island (Cycladic) style building generator (Layer 1: PCG).

Builds Santorini/Mykonos-style buildings featuring:
- Stacked, inset upper floors with rooftop terraces
- Blue terracotta accents on doors and window frames
- Exterior staircase to the roof terrace
- Iconic flat parapets, blue domes, or stepped terraced roofs
"""
import math
from gdpc import Editor, Block
from gdpc.vector_tools import ivec3

from src.schema import BuildingParams, RoofType, Decoration


FLOOR_HEIGHT = 4  # 3 walls + 1 ceiling/floor between
AIR = Block("minecraft:air")
#BLUE_TRIM = Block("minecraft:blue_terracotta")


class GreekIslandBuilder:
    def __init__(self, editor: Editor):
        self.editor = editor

    def build(self, params: BuildingParams, origin: ivec3, fill_below: int=1) -> None:
        wall = Block(params.palette.wall)
        roof = Block(params.palette.roof)
        accent = Block(params.palette.accent)
        trim = Block(params.palette.trim)
        w, d = params.footprint.width, params.footprint.depth

        # Plan each floor's footprint: upper floors step in for that Cycladic look
        floor_specs = []  # (dx, dz, fw, fd)
        for f in range(params.floors):
            if f == 0:
                floor_specs.append((0, 0, w, d))
            else:
                pdx, _, pw, pd = floor_specs[-1]
                nw = max(5, pw - 2)
                nd = max(5, pd - 1)
                floor_specs.append((pdx + 1, 0, nw, nd))  # inset 1 on the left side

        # Foundation under full ground-floor footprint
        for x in range(w):
            for z in range(d):
                for depth in range(1, fill_below +1):
                    self.editor.placeBlock(origin + ivec3(x, -depth, z), accent)

        # Build each floor
        for f, (dx, dz, fw, fd) in enumerate(floor_specs):
            fo = origin + ivec3(dx, f * FLOOR_HEIGHT, dz)
            self._walls(fo, fw, fd, wall)
            if f == 0:
                self._door_with_trim(fo, fw, trim)
            self._windows_with_trim(fo, fw, fd, trim)
            if f > 0:  # interior floor for upper floors
                for x in range(fw):
                    for z in range(fd):
                        self.editor.placeBlock(fo + ivec3(x, -1, z), wall)

        # Rooftop terraces: the exposed top of each lower floor
        for f in range(params.floors - 1):
            cdx, cdz, cw, cd = floor_specs[f]
            ndx, ndz, nw, nd = floor_specs[f + 1]
            rx, rz = ndx - cdx, ndz - cdz
            terrace_y = (f + 1) * FLOOR_HEIGHT - 1
            terrace_o = origin + ivec3(cdx, terrace_y, cdz)
            for x in range(cw):
                for z in range(cd):
                    under_upper = (rx <= x < rx + nw and rz <= z < rz + nd)
                    if not under_upper:
                        self.editor.placeBlock(terrace_o + ivec3(x, 0, z), accent)
                        # Parapet on outer edge of lower floor
                        on_edge = (x == 0 or x == cw - 1 or z == 0 or z == cd - 1)
                        if on_edge:
                            self.editor.placeBlock(terrace_o + ivec3(x, 1, z), wall)

        # Top floor's actual roof
        top_dx, top_dz, top_w, top_d = floor_specs[-1]
        roof_y = params.floors * FLOOR_HEIGHT - 1
        ro = origin + ivec3(top_dx, roof_y, top_dz)
        self._build_roof(params.roof_type, ro, top_w, top_d, wall, roof)

        # External staircase to the first rooftop terrace (if 2+ floors)
        if params.floors >= 2:
            self._exterior_stairs(origin, w, d, accent)

        self._decorations(params, origin, w, d, accent)

    # ---- walls and openings ----

    def _walls(self, o, w, d, wall):
        for y in range(3):
            for x in range(w):
                self.editor.placeBlock(o + ivec3(x, y, 0), wall)
                self.editor.placeBlock(o + ivec3(x, y, d - 1), wall)
            for z in range(d):
                self.editor.placeBlock(o + ivec3(0, y, z), wall)
                self.editor.placeBlock(o + ivec3(w - 1, y, z), wall)

    def _door_with_trim(self, o, w, trim):
        """Centered front-wall door with prominent blue terracotta frame."""
        dx = w // 2
        # Blue frame on both sides, 3 high
        for y in range(3):
            self.editor.placeBlock(o + ivec3(dx - 1, y, 0), trim)
            self.editor.placeBlock(o + ivec3(dx + 1, y, 0), trim)
        # Blue lintel above the doorway
        self.editor.placeBlock(o + ivec3(dx, 2, 0), trim)
        # Doorway itself
        self.editor.placeBlock(o + ivec3(dx, 0, 0), AIR)
        self.editor.placeBlock(o + ivec3(dx, 1, 0), AIR)

    def _windows_with_trim(self, o, w, d, trim):
        """Windows in all walls, with blue frames above and below."""
        # Front and back walls
        for x in range(2, w - 2, 3):
            self._framed_window(o + ivec3(x, 1, 0), trim)
            self._framed_window(o + ivec3(x, 1, d - 1), trim)
        # Left and right walls
        for z in range(2, d - 2, 3):
            self._framed_window(o + ivec3(0, 1, z), trim)
            self._framed_window(o + ivec3(w - 1, 1, z), trim)

    def _framed_window(self, pos, trim):
        self.editor.placeBlock(pos + ivec3(0, -1, 0), trim)
        self.editor.placeBlock(pos + ivec3(0, 1, 0), trim)
        self.editor.placeBlock(pos, AIR)

    def _exterior_stairs(self, origin, w, d, accent):
        """Stairs running up the back of the building to the rooftop terrace."""
        stair_z = d  # one block out behind the building
        for step in range(FLOOR_HEIGHT):
            x = w - 1 - step
            if x < 0:
                break
            self.editor.placeBlock(origin + ivec3(x, step, stair_z), accent)
            for fill_y in range(step):
                self.editor.placeBlock(origin + ivec3(x, fill_y, stair_z), accent)

    # ---- roofs ----

    def _build_roof(self, rtype, o, w, d, wall, roof):
        if rtype == RoofType.FLAT:
            self._roof_flat(o, w, d, wall, roof)
        elif rtype == RoofType.DOMED:
            self._roof_domed(o, w, d, roof)
        elif rtype == RoofType.GABLED:
            self._roof_gabled(o, w, d, wall, roof)
        elif rtype == RoofType.TERRACED:
            self._roof_terraced(o, w, d, roof)

    def _roof_flat(self, o, w, d, wall, roof):
        for x in range(w):
            for z in range(d):
                self.editor.placeBlock(o + ivec3(x, 0, z), roof)
        for x in range(w):
            self.editor.placeBlock(o + ivec3(x, 1, 0), wall)
            self.editor.placeBlock(o + ivec3(x, 1, d - 1), wall)
        for z in range(d):
            self.editor.placeBlock(o + ivec3(0, 1, z), wall)
            self.editor.placeBlock(o + ivec3(w - 1, 1, z), wall)

    def _roof_domed(self, o, w, d, roof):
        cx, cz = (w - 1) / 2, (d - 1) / 2
        r = min(w, d) / 2
        for x in range(w):
            for z in range(d):
                dist = math.sqrt((x - cx) ** 2 + (z - cz) ** 2)
                if dist <= r:
                    h = int(round(math.sqrt(max(0, r ** 2 - dist ** 2))))
                    for y in range(h + 1):
                        self.editor.placeBlock(o + ivec3(x, y, z), roof)

    def _roof_gabled(self, o, w, d, wall, roof):
        for x in range(w):
            h = min(x, w - 1 - x)
            for z in range(d):
                self.editor.placeBlock(o + ivec3(x, h, z), roof)
            for y in range(h):
                self.editor.placeBlock(o + ivec3(x, y, 0), wall)
                self.editor.placeBlock(o + ivec3(x, y, d - 1), wall)

    def _roof_terraced(self, o, w, d, roof):
        inset, y = 0, 0
        while w - 2 * inset > 0 and d - 2 * inset > 0:
            for x in range(inset, w - inset):
                for z in range(inset, d - inset):
                    self.editor.placeBlock(o + ivec3(x, y, z), roof)
            inset += 1
            y += 1

    # ---- decorations ----

    def _decorations(self, params, o, w, d, accent):
        decos = params.decorations
        if Decoration.STONE_PATH in decos:
            for x in range(-1, w + 1):
                self.editor.placeBlock(o + ivec3(x, -1, -1), accent)
                self.editor.placeBlock(o + ivec3(x, -1, d), accent)
            for z in range(-1, d + 1):
                self.editor.placeBlock(o + ivec3(-1, -1, z), accent)
                self.editor.placeBlock(o + ivec3(w, -1, z), accent)
        if Decoration.FLOWER_POTS in decos:
            dx = w // 2
            pot = Block("minecraft:flower_pot")
            self.editor.placeBlock(o + ivec3(dx - 2, 0, -1), pot)
            self.editor.placeBlock(o + ivec3(dx + 2, 0, -1), pot)
        if Decoration.CHIMNEY in decos:
            cy = params.floors * FLOOR_HEIGHT + 1
            for y in range(3):
                self.editor.placeBlock(o + ivec3(w - 2, cy + y, 1), accent)
        if Decoration.PERGOLA in decos:
            dx = w // 2
            beam = Block("minecraft:spruce_planks")
            for x in range(dx - 1, dx + 2):
                for z in range(-3, 0):
                    self.editor.placeBlock(o + ivec3(x, 3, z), beam)
        if Decoration.BELL_TOWER in decos:
            tx, tz = w // 2, d // 2
            ty = params.floors * FLOOR_HEIGHT + 1
            for y in range(4):
                self.editor.placeBlock(o + ivec3(tx, ty + y, tz), accent)
            self.editor.placeBlock(o + ivec3(tx, ty + 4, tz), Block("minecraft:bell"))

        if Decoration.CROSS in decos:
            cross = Block("minecraft:white_concrete")
            cx, cz = w // 2, d // 2
            cy = params.floors * FLOOR_HEIGHT + 2
            for y in range(5):
                self.editor.placeBlock(o + ivec3(cx, cy + y, cz), cross)
            self.editor.placeBlock(o + ivec3(cx - 1, cy + 3, cz), cross)
            self.editor.placeBlock(o + ivec3(cx + 1, cy + 3, cz), cross)