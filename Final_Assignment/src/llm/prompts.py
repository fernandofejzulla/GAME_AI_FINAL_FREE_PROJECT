"""Prompt templates for the LLM building parameter generator."""
import json
from src.schema import (
    GREEK_WALL_BLOCKS, GREEK_ROOF_BLOCKS,
    GREEK_ACCENT_BLOCKS, GREEK_TRIM_BLOCKS,
)


SYSTEM_INSTRUCTIONS = f"""You generate parameters for procedurally-generated buildings in a Greek-island (Cycladic / Santorini / Mykonos) Minecraft village.

Each building is defined by a BuildingParams JSON object with these fields:
- style: one of "cycladic", "traditional", "seaside", "hillside"
- floors: integer, 1 or 2
- roof_type: one of "flat", "domed", "gabled", "terraced"
- palette: object with four Minecraft block IDs:
    - wall: must be one of {GREEK_WALL_BLOCKS}
    - roof: must be one of {GREEK_ROOF_BLOCKS}
    - accent: must be one of {GREEK_ACCENT_BLOCKS}
    - trim: must be one of {GREEK_TRIM_BLOCKS}
- footprint: object with width (5-12) and depth (5-12)
- decorations: list of strings, each one of "chimney", "pergola", "stone_path", "flower_pots", "bell_tower", "shutters", "cross". Length 0-4.

Design guidelines:
- White walls (white_concrete, smooth_quartz) dominate the Cycladic aesthetic.
- Blue roofs (blue_concrete, light_blue_concrete) belong on chapels and prominent buildings.
- Use "domed" roof only for chapels.
- Use "cross" decoration only for religious buildings (chapels/churches).
- Use "bell_tower" only on chapels.
- Stone accents (cobblestone, stone_bricks) fit traditional and hillside styles.
- Keep palette coherent — don't mix warm terracotta with bright Santorini blues."""


def zero_shot_prompt(concept: str) -> str:
    return f"""{SYSTEM_INSTRUCTIONS}

Generate BuildingParams JSON for this concept:
"{concept}"

Return only the JSON object, no explanation."""


FEW_SHOT_EXAMPLES = [
    {
        "concept": "small Cycladic cottage",
        "params": {
            "style": "cycladic", "floors": 1, "roof_type": "flat",
            "palette": {
                "wall": "minecraft:white_concrete",
                "roof": "minecraft:smooth_quartz",
                "accent": "minecraft:cobblestone",
                "trim": "minecraft:blue_terracotta",
            },
            "footprint": {"width": 7, "depth": 8},
            "decorations": ["stone_path", "flower_pots"],
        },
    },
    {
        "concept": "blue-domed chapel with bell tower",
        "params": {
            "style": "cycladic", "floors": 1, "roof_type": "domed",
            "palette": {
                "wall": "minecraft:white_concrete",
                "roof": "minecraft:blue_concrete",
                "accent": "minecraft:cobblestone",
                "trim": "minecraft:blue_terracotta",
            },
            "footprint": {"width": 7, "depth": 7},
            "decorations": ["stone_path", "bell_tower"],
        },
    },
    {
        "concept": "two-story stone hillside cottage",
        "params": {
            "style": "hillside", "floors": 2, "roof_type": "terraced",
            "palette": {
                "wall": "minecraft:white_terracotta",
                "roof": "minecraft:smooth_quartz",
                "accent": "minecraft:cobblestone",
                "trim": "minecraft:light_blue_terracotta",
            },
            "footprint": {"width": 9, "depth": 8},
            "decorations": ["chimney", "stone_path", "pergola"],
        },
    },
]


def few_shot_prompt(concept: str) -> str:
    examples = "\n\n".join(
        f'Concept: "{ex["concept"]}"\nJSON:\n{json.dumps(ex["params"], indent=2)}'
        for ex in FEW_SHOT_EXAMPLES
    )
    return f"""{SYSTEM_INSTRUCTIONS}

Here are some examples of correct outputs:

{examples}

Now generate BuildingParams JSON for this concept:
"{concept}"

Return only the JSON object, no explanation."""