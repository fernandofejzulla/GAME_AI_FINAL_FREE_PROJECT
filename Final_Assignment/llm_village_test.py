"""End-to-end demo: LLM generates building parameters, generator builds them."""
from gdpc import Editor
from gdpc.vector_tools import ivec3

from src.llm.client import BuildingLLM
from src.pcg.generator import GreekIslandBuilder
from src.pcg.placement import load_heightmap, evaluate_footprint, is_water_at


CONCEPTS = [
    "small Cycladic chapel with a cross on top",
    "two-story Mykonos seaside cottage with a pergola",
    "traditional inland village house with chimney and gabled roof",
    "tiny white watchtower",
    "blue-domed church with bell tower",
]


def main():
    print("Generating building parameters via Gemini (few-shot strategy)...")
    llm = BuildingLLM()
    buildings = []
    for concept in CONCEPTS:
        print(f"  '{concept}'... ", end="", flush=True)
        params = llm.generate(concept, strategy="few_shot")
        print(f"OK ({params.style.value}/{params.roof_type.value}, "
              f"{params.footprint.width}x{params.footprint.depth})")
        buildings.append((concept, params))

    print("\nPlacing in Minecraft...")
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    heightmap, rect = load_heightmap(editor, build_area)
    builder = GreekIslandBuilder(editor)

    start_x = build_area.offset.x + 6
    start_z = build_area.offset.z + 6
    spacing = 16

    placed = 0
    for i, (concept, params) in enumerate(buildings):
        x = start_x + (i % 3) * spacing
        z = start_z + (i // 3) * spacing
        w, d = params.footprint.width, params.footprint.depth

        result = evaluate_footprint(heightmap, rect, x, z, w, d)
        if result is None:
            print(f"  skip '{concept}': out of bounds or too sloped")
            continue
        ground_y, fill_below = result
        if is_water_at(editor, x, ground_y, z):
            print(f"  skip '{concept}': water")
            continue

        origin = ivec3(x, ground_y + 1, z)
        print(f"  build '{concept}' at {origin}")
        builder.build(params, origin, fill_below=fill_below)
        placed += 1

    editor.flushBuffer()
    print(f"\nLLM-generated village complete: {placed}/{len(CONCEPTS)} buildings.")


if __name__ == "__main__":
    main()