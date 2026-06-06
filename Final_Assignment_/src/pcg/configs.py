"""Shared building configurations for village generation."""
import random
from src.schema import (
    BuildingParams, Style, RoofType, Decoration, Palette, Footprint,
)


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


def random_house(rng: random.Random) -> BuildingParams:
    return BuildingParams(
        style=rng.choice(list(Style)),
        floors=rng.choice([1]),
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


def chapel(rng: random.Random) -> BuildingParams:
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


def small_church(rng: random.Random) -> BuildingParams:
    return BuildingParams(
        style=Style.CYCLADIC, floors=1, roof_type=RoofType.FLAT,
        palette=Palette(
            wall="minecraft:white_concrete", roof="minecraft:smooth_quartz",
            accent="minecraft:white_terracotta", trim="minecraft:white_concrete",
        ),
        footprint=Footprint(width=5, depth=7),
        decorations=[Decoration.STONE_PATH, Decoration.CROSS],
    )