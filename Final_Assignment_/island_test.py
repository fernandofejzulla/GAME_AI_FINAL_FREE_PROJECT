"""Generate an island in the current build area and teleport the player above it."""
from gdpc import Editor

from src.pcg.island import generate_island


def main():
    seed = 42
    editor = Editor(buffering=True)
    build_area = editor.getBuildArea()
    print(f"Build area: {build_area}")

    print("Generating island...")
    heightmap = generate_island(editor, build_area, seed=seed)
    editor.flushBuffer()

    cx = build_area.offset.x + build_area.size.x // 2
    cz = build_area.offset.z + build_area.size.z // 2
    cy = int(heightmap.max()) + 15
    editor.runCommand(f"tp @s {cx} {cy} {cz}")

    print(f"\nIsland generated.")
    print(f"  Max height above sea: {int(heightmap.max()) - 63} blocks")
    print(f"  Land columns: {int((heightmap > 63).sum())}")
    print(f"  Teleported to ({cx}, {cy}, {cz}). Look down.")


if __name__ == "__main__":
    main()