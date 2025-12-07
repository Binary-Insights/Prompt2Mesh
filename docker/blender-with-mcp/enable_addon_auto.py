"""
Auto-enable and start the Blender MCP addon
Run this script in Blender to automatically enable and start the MCP server
"""
import bpy
import addon_utils
import sys

def enable_and_start_mcp():
    """Enable the Blender MCP addon and start its server"""
    
    print("="*60)
    print("🚀 Blender MCP Auto-Start Script")
    print("="*60)
    
    # Enable the addon
    addon_module = "blender_mcp_addon"
    
    # List all available addons to verify our addon is present
    print("\n📦 Checking for MCP addon...")
    addon_found = False
    for mod in addon_utils.modules():
        if addon_module in mod.__name__:
            addon_found = True
            print(f"✅ Found addon module: {mod.__name__}")
            break
    
    if not addon_found:
        print(f"❌ Addon '{addon_module}' not found in Blender's addon path")
        print("Available addon paths:")
        for path in bpy.utils.script_paths():
            print(f"  - {path}")
        return False
    
    # Check if already enabled
    is_enabled = addon_utils.check(addon_module)[1]
    
    if not is_enabled:
        print(f"\n🔧 Enabling addon: {addon_module}")
        try:
            addon_utils.enable(addon_module, default_set=True, persistent=True)
            # Save preferences to persist the enabled state
            bpy.ops.wm.save_userpref()
            print(f"✅ Addon enabled and saved to preferences")
        except Exception as e:
            print(f"❌ Failed to enable addon: {e}")
            import traceback
            traceback.print_exc()
            return False
    else:
        print(f"✅ Addon already enabled: {addon_module}")
    
    # Wait a moment for addon to fully load
    import time
    time.sleep(1)
    
    # Verify the addon loaded its classes and properties
    if not hasattr(bpy.types, 'blendermcp_server'):
        print("⚠️  Creating server instance...")
        try:
            # Import the addon to trigger its register() function
            import importlib
            addon_mod = sys.modules.get(addon_module)
            if addon_mod:
                importlib.reload(addon_mod)
        except Exception as e:
            print(f"⚠️  Could not reload addon: {e}")
    
    # Start the MCP server
    try:
        # Check if server is already running
        if hasattr(bpy.types, 'blendermcp_server') and bpy.types.blendermcp_server:
            if bpy.types.blendermcp_server.running:
                print("✅ MCP server already running on port 9876")
                return True
        
        # Check scene property
        scene = bpy.context.scene
        if hasattr(scene, 'blendermcp_server_running'):
            if scene.blendermcp_server_running:
                print("✅ MCP server already running (scene flag set)")
                return True
        
        # Start the server using the operator
        print("\n🚀 Starting MCP server...")
        
        # Ensure we have a valid context
        if not bpy.context.scene:
            print("❌ No valid scene context available")
            return False
        
        # Execute the operator
        result = bpy.ops.blendermcp.start_server()
        
        if result == {'FINISHED'}:
            print("✅ MCP server started successfully on port 9876")
            
            # Verify it's running
            time.sleep(1)
            if hasattr(bpy.types, 'blendermcp_server') and bpy.types.blendermcp_server:
                if bpy.types.blendermcp_server.running:
                    print("✅ Server confirmed running")
                    return True
            
            # Check scene flag as backup
            if hasattr(scene, 'blendermcp_server_running') and scene.blendermcp_server_running:
                print("✅ Server confirmed running (via scene flag)")
                return True
            
            print("⚠️  Server start command executed but status unclear")
            return True
        else:
            print(f"⚠️  Server start returned: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to start MCP server: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Starting Blender MCP Auto-Configuration...")
    print("="*60 + "\n")
    
    success = enable_and_start_mcp()
    
    print("\n" + "="*60)
    if success:
        print("🎉 Blender MCP is ready!")
        print("="*60)
        print("📍 Server: blender:9876")
        print("🌐 Web UI: http://localhost:3000")
        print("="*60)
        sys.exit(0)
    else:
        print("❌ Failed to initialize Blender MCP")
        print("="*60)
        print("Please enable manually from Blender UI")
        print("="*60)
        sys.exit(1)
