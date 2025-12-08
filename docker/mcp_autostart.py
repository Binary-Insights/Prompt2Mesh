"""
Blender startup script to auto-start MCP server
This runs when Blender GUI starts
"""
import bpy

def start_mcp_server():
    """Start MCP server after Blender fully initializes"""
    import os
    
    # Only run in Docker/container environments
    if not (os.path.exists("/.dockerenv") or os.path.exists("/run/.containerenv")):
        return None
    
    print("🐳 Blender GUI startup detected - Starting MCP server...")
    
    try:
        # Check if server is already running
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server:
            if bpy.types.blendermcp_server.running:
                print("✅ MCP server already running")
                return None
        
        # Check if port is in use
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 9876))
        sock.close()
        
        if result == 0:
            print("✅ MCP server already listening on port 9876")
            return None
        
        # Start the server
        print("🚀 Starting MCP server on port 9876...")
        bpy.ops.blendermcp.start_server()
        print("✅ MCP server started successfully")
        
    except Exception as e:
        print(f"⚠️  MCP auto-start failed: {e}")
        import traceback
        traceback.print_exc()
    
    return None  # Don't repeat

def register():
    """Required register function for Blender startup scripts"""
    # Register timer to run after Blender initializes
    bpy.app.timers.register(start_mcp_server, first_interval=3.0)
    print("📋 MCP auto-start timer registered")

def unregister():
    """Required unregister function for Blender startup scripts"""
    pass

# Auto-register when loaded as startup script
if __name__ != "__main__":
    register()
