"""
Auto-enable and start the Blender MCP addon
Run this script in Blender to automatically enable and start the MCP server
"""
import bpy
import addon_utils

def enable_and_start_mcp():
    """Enable the Blender MCP addon and start its server"""
    
    # Enable the addon
    addon_module = "blender_mcp_addon"
    
    # Check if already enabled
    is_enabled = addon_utils.check(addon_module)[1]
    
    if not is_enabled:
        print(f"Enabling addon: {addon_module}")
        try:
            addon_utils.enable(addon_module, default_set=True)
            print(f"✅ Addon enabled: {addon_module}")
        except Exception as e:
            print(f"❌ Failed to enable addon: {e}")
            return False
    else:
        print(f"✅ Addon already enabled: {addon_module}")
    
    # Wait a moment for addon to fully load
    import time
    time.sleep(0.5)
    
    # Start the MCP server
    try:
        # Check if server is already running
        scene = bpy.context.scene
        if hasattr(scene, 'blendermcp_server_running') and scene.blendermcp_server_running:
            print("✅ MCP server already running")
            return True
        
        # Start the server using the operator
        print("Starting MCP server...")
        bpy.ops.blendermcp.start_server()
        print("✅ MCP server started on port 9876")
        return True
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = enable_and_start_mcp()
    if success:
        print("\n" + "="*60)
        print("🎉 Blender MCP is ready!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Failed to initialize Blender MCP")
        print("="*60)
