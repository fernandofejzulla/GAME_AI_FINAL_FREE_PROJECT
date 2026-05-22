from gdpc import Editor, Block

editor = Editor()
buildArea = editor.getBuildArea()
print(f"Build area: {buildArea}")
print(f"Center: {buildArea.center}")

# Place a gold block at the center of the build area
editor.placeBlock(buildArea.center, Block("gold_block"))
print(f"Placed a gold block at {buildArea.center}")