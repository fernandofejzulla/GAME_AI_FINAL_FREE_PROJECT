"""
Building parameter schema for a Greek-island settlement generator
"""
from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator


#Style variants within the Greek-island aesthetic
class Style(str, Enum):
    CYCLADIC = "cycladic"        #Santorini-style: pure white walls, flat or domed roof
    TRADITIONAL = "traditional"  #Stone-and-whitewash village house, pitched roof
    SEASIDE = "seaside"          #Smaller, weathered, often with a pergola or porch
    HILLSIDE = "hillside"        #Terraced into terrain, stone-heavy base


class RoofType(str, Enum):
    FLAT = "flat"   #Iconic Cycladic flat roof
    DOMED = "domed"     #Blue church / chapel dome
    GABLED = "gabled" #Pitched, traditional inland houses
    TERRACED = "terraced" #Step-down hillside


class Decoration(str, Enum):
    CHIMNEY = "chimney"
    PERGOLA = "pergola"    #Wooden shaded patio
    STONE_PATH = "stone_path"  #Path/border around the building
    FLOWER_POTS = "flower_pots"
    BELL_TOWER = "bell_tower" #For chapels
    SHUTTERS = "shutters"  #Blue-painted window shutters
    CROSS = "cross"


#Constrained palettes (the LLM must choose from these)
GREEK_WALL_BLOCKS = [
    "minecraft:white_concrete",
    "minecraft:smooth_quartz",
    "minecraft:quartz_block",
    "minecraft:white_terracotta",
    "minecraft:calcite",
    "minecraft:diorite",
]

GREEK_ROOF_BLOCKS = [
    "minecraft:blue_concrete",        #Santorini chapel dome
    "minecraft:light_blue_concrete",
    "minecraft:blue_terracotta",
    "minecraft:lapis_block",
    "minecraft:terracotta",           #Warmer, for traditional/inland
    "minecraft:smooth_quartz",        #Flat white roof
    "minecraft:white_concrete"
]

GREEK_ACCENT_BLOCKS = [
    "minecraft:cobblestone",
    "minecraft:stone_bricks",
    "minecraft:mossy_cobblestone",
    "minecraft:spruce_planks",         #Doors, shutters
    "minecraft:dark_oak_planks",
    "minecraft:polished_diorite",
    "minecraft:calcite",
    "minecraft:white_terracotta",
]

GREEK_TRIM_BLOCKS = [
    "minecraft:blue_terracotta",
    "minecraft:light_blue_terracotta",
    "minecraft:white_terracotta",
    "minecraft:blue_concrete",
    "minecraft:light_blue_concrete",
    "minecraft:white_concrete",
    "minecraft:smooth_quartz",
    "minecraft:quartz_block",
    "minecraft:white_terracotta",
]

class Palette(BaseModel):
    wall: str
    roof: str
    accent: str
    trim: str = "minecraft:blue_terracotta"

    @field_validator("wall")
    @classmethod
    def valid_wall(cls, v):
        if v not in GREEK_WALL_BLOCKS:
            raise ValueError(f"wall must be one of {GREEK_WALL_BLOCKS}")
        return v

    @field_validator("roof")
    @classmethod
    def valid_roof(cls, v):
        if v not in GREEK_ROOF_BLOCKS:
            raise ValueError(f"roof must be one of {GREEK_ROOF_BLOCKS}")
        return v

    @field_validator("accent")
    @classmethod
    def valid_accent(cls, v):
        if v not in GREEK_ACCENT_BLOCKS:
            raise ValueError(f"accent must be one of {GREEK_ACCENT_BLOCKS}")
        return v

    @field_validator("trim")
    @classmethod
    def valid_trim(cls, v):
        if v not in GREEK_TRIM_BLOCKS:
            raise ValueError(f"trim must be one of {GREEK_TRIM_BLOCKS}")
        return v


class Footprint(BaseModel):
    width: int = Field(..., ge=5, le=12)
    depth: int = Field(..., ge=5, le=12)


class BuildingParams(BaseModel):
    """Complete parameter set defining one building in the Greek-island style"""
    style: Style
    floors: int = Field(..., ge=1, le=2)   #Greek island buildings are typically 1-2 floors
    roof_type: RoofType
    palette: Palette
    footprint: Footprint
    decorations: List[Decoration] = Field(default_factory=list)

    @field_validator("decorations")
    @classmethod
    def unique_decorations(cls, v):
        return list(dict.fromkeys(v))  #dedupe, preserve order


#Hardcoded example: a classic Santorini cottage
EXAMPLE_PARAMS = BuildingParams(
    style=Style.CYCLADIC,
    floors=2,
    roof_type=RoofType.FLAT,
    palette=Palette(
        wall="minecraft:white_concrete",
        roof="minecraft:smooth_quartz",
        accent="minecraft:cobblestone",
        trim="minecraft:blue_terracotta"
    ),
    footprint=Footprint(width=11, depth=10),
    decorations=[Decoration.STONE_PATH, Decoration.FLOWER_POTS],
)


if __name__ == "__main__":
    print(EXAMPLE_PARAMS.model_dump_json(indent=2))