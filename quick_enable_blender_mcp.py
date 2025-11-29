"""
Quick Blender MCP Addon Enabler
Copy and paste this entire script into Blender's Scripting tab and click "Run Script"
"""
import bpy
import addon_utils

# Enable the addon
addon_name = "blender_mcp_addon"

# Enable it
enabled, loaded = addon_utils.check(addon_name)
if not enabled:
    addon_utils.enable(addon_name, default_set=True)
    print(f"✅ Enabled addon: {addon_name}")
else:
    print(f"✅ Addon already enabled: {addon_name}")

# Save preferences
bpy.ops.wm.save_userpref()
print("✅ Preferences saved")

# Start the server
try:
    bpy.ops.blendermcp.start_server()
    print("✅ MCP Server started on port 9876")
    print("\n" + "="*60)
    print("🎉 Blender MCP is ready! You can now connect from Streamlit")
    print("="*60)
except Exception as e:
    print(f"⚠️ Server might already be running or error: {e}")
    print("Check the BlenderMCP panel in the sidebar (press N key)")
