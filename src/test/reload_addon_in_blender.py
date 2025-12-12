"""
Force reload addon in Blender
Run this from Blender's Python Console (Scripting workspace)
"""

import bpy
import sys

# Disable the addon
bpy.ops.preferences.addon_disable(module="addon")

# Remove from sys.modules to force reload
if "addon" in sys.modules:
    del sys.modules["addon"]

print("Addon unloaded from memory")

# Re-enable the addon (this will reload from disk)
bpy.ops.preferences.addon_enable(module="addon")

print("Addon reloaded from disk")
print("Now start the server from the BlenderMCP panel")
