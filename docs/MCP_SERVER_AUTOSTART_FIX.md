# MCP Server Auto-Start Fix

## Problem Identified

The MCP server addon in Blender was not starting automatically in Kubernetes, even though it showed "Running" in the UI. Investigation revealed the root cause:

### Symptoms
- Addon UI showed "Running on port 9876" 
- Backend reported "Disconnected from MCP server"
- `netstat` showed no process listening on port 9876
- User prompts executed but no 3D objects were created in Blender

### Root Cause
The issue was a **race condition during Blender addon initialization**:

1. During container startup, the Blender addon gets registered/unregistered multiple times:
   ```
   BlenderMCP addon registered
   BlenderMCP addon unregistered  
   BlenderMCP addon registered
   BlenderMCP addon unregistered
   ```

2. Each time `register()` is called, it registers an auto-start timer:
   ```python
   bpy.app.timers.register(auto_start_server, first_interval=2.0)
   ```

3. When multiple timers fire simultaneously after 2 seconds, they all try to bind to port 9876

4. Result: `[Errno 98] Address already in use` error
   - First timer successfully binds → starts server
   - Subsequent timers fail → but exceptions are caught silently
   - Server then stops because the addon unregisters
   - Final state: No server running but UI thinks it is

## Solution Implemented

Modified the auto-start logic to check if port 9876 is already in use before attempting to bind:

```python
def auto_start_server():
    try:
        # Check if server is already running
        if hasattr(bpy.types, "blendermcp_server") and bpy.types.blendermcp_server and bpy.types.blendermcp_server.running:
            print("✅ MCP server already running")
            return None
        
        # Check if port is already in use (another timer might have started it)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 9876))
        sock.close()
        
        if result == 0:
            print("✅ MCP server already listening on port 9876")
            return None
        
        # Port is free, start the server
        print("🚀 Auto-starting MCP server on port 9876...")
        bpy.ops.blendermcp.start_server()
        print("✅ MCP server started automatically")
    except Exception as e:
        print(f"⚠️  Auto-start failed: {e}")
        import traceback
        traceback.print_exc()
    return None
```

### Key Improvements
1. **Port availability check**: Before starting, check if something is already listening on port 9876
2. **Server instance check**: Verify `bpy.types.blendermcp_server.running` flag
3. **Better error handling**: Added traceback printing for debugging

## Testing

### To Verify the Fix
1. **Delete the existing Blender pod** (if any):
   ```bash
   kubectl delete pod blender-<username>-<id> -n prompt2mesh
   ```

2. **Access Blender UI** from frontend to trigger new pod creation

3. **Check pod logs** for successful auto-start:
   ```bash
   kubectl logs blender-<username>-<id> -n prompt2mesh | grep -i "mcp\|auto-start"
   ```

   Expected output:
   ```
   🐳 Docker environment detected - Auto-starting MCP server...
   🚀 Auto-starting MCP server on port 9876...
   ✅ MCP server started automatically
   ```

4. **Verify port is listening**:
   ```bash
   kubectl exec blender-<username>-<id> -n prompt2mesh -- netstat -tlnp | grep 9876
   ```

5. **Test 3D object creation**:
   - Submit a prompt through the frontend
   - Check if objects appear in Blender scene

## Files Modified
- `src/addon/__init__.py` - Added port availability check to auto-start function
- Docker image rebuilt and pushed to ECR: `prompt2mesh/blender-mcp:latest`

## Deployment Status
- ✅ Code committed to `cloud` branch (commit: 59589fe)
- ✅ Docker image rebuilt with fix
- ✅ Image pushed to ECR
- ⏳ Waiting for next Blender pod creation to verify fix

## Next Steps
1. Create a new Blender session to test the fix
2. Monitor logs for successful auto-start
3. Test end-to-end 3D object generation
4. If successful, merge to main branch
