# Blender MCP Addon Manual Activation Guide

## Problem
The Blender MCP addon is installed but not enabled, so the server on port 9876 is not running.

## Solution: Enable the Addon via Blender Web UI

### Step 1: Access Blender Web UI
1. Open your browser
2. Go to: **http://localhost:3000**
3. You should see the Blender interface via KasmVNC

### Step 2: Enable the Addon
1. In Blender, go to **Edit** menu → **Preferences** (or press `Ctrl+Alt+U` / `Cmd+,`)
2. Click on **Add-ons** tab (on the left sidebar)
3. In the search box at top-right, type: **`Blender MCP`**
4. You should see **"Interface: Blender MCP"** in the list
5. **Check the checkbox** next to it to enable it
6. Click **Save Preferences** (bottom-left button)

### Step 3: Start the MCP Server
1. In the 3D Viewport, press **`N`** key to open the sidebar (if not already open)
2. Look for the **BlenderMCP** tab in the sidebar
3. Click the **"Connect to Claude"** button
4. You should see a message confirming the server started on port 9876

### Step 4: Verify Connection
Once you click "Connect to Claude", the server should start and you'll see in the panel:
- ✅ Server Running status indicator
- The port number (9876)

### Step 5: Test from Streamlit
1. Go back to your Streamlit UI: **http://localhost:8501**
2. Navigate to **Artisan Agent** page
3. Click **"Connect to Blender"** in the sidebar
4. You should now see a successful connection!

---

## Alternative: Quick Test Commands

If you want to verify the server is running, run this from your terminal:

```powershell
# Check if port 9876 is listening
docker exec prompt2mesh-blender netstat -tulpn | Select-String "9876"
```

If you see output, the server is running! If not, follow the manual steps above.

---

## Troubleshooting

**Q: I don't see the "Blender MCP" addon in preferences**  
A: The addon file might not be in the right location. Check:
```powershell
docker exec prompt2mesh-blender ls -la /config/.config/blender/5.0/scripts/addons/
```
You should see `blender_mcp_addon.py`

**Q: I enabled it but the server isn't starting**  
A: Check Blender's console output:
```powershell
docker logs prompt2mesh-blender --tail 50
```

**Q: Can I auto-enable this on startup?**  
A: Currently, Blender addons in Docker require manual activation via the UI. The addon is installed, but Blender's preference system doesn't auto-enable custom addons by default.

---

## Next Steps After Enabling

Once the addon is enabled and server is running:
1. ✅ You can connect from Streamlit
2. ✅ Send prompts to create 3D models
3. ✅ View results in real-time in Blender Web UI (http://localhost:3000)
4. ✅ Screenshot functionality will work
5. ✅ All Blender MCP tools will be available to Claude
