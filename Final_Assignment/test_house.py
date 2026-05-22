"""Build one Greek-island building using the hardcoded EXAMPLE_PARAMS."""
from gdpc import Editor
from gdpc.vector_tools import ivec3

from src.pcg.generator import GreekIslandBuilder
from src.schema import EXAMPLE_PARAMS


def main():
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    print(f"Build area: {build_area}")

    # Build inset from the build-area corner, one block above its floor
    origin = build_area.offset + ivec3(5, 1, 5)
    print(f"Origin: {origin}")
    print(f"Building: {EXAMPLE_PARAMS.style.value} / {EXAMPLE_PARAMS.roof_type.value}")

    builder = GreekIslandBuilder(editor)
    builder.build(EXAMPLE_PARAMS, origin)
    editor.flushBuffer()
    print("Done.")


if __name__ == "__main__":
    main()