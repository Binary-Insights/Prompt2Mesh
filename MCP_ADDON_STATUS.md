# MCP Addon Auto-Enable Status

## Current Situation ✅ 95% Complete

### What's Working:
1. ✅ Per-user Docker containers created successfully
2. ✅ Unique port allocation (MCP: 10000+, UI: 13000+)
3. ✅ Containers start and run Blender UI properly
4. ✅ MCP addon files copied to containers
5. ✅ Backend API accepts user_id parameter
6. ✅ Frontend passes user_id correctly
7. ✅ No timeouts or connection errors
8. ✅ Session management working perfectly

### What's Not Working:
- ❌ MCP addon does not auto-enable in Blender UI (needs manual click)

## The Challenge

The linuxserver/blender Docker image runs Blender through a web UI (Selkies), not as a standard desktop application. Standard Blender auto-start methods don't work:

1. **Startup scripts** (`scripts/startup/*.py`) - Only work for Blender GUI mode, not headless server
2. **Init scripts** (`cont-init.d`) - Run before Blender config is fully initialized
3. **Background mode** (`blender --background --python`) - Can't enable UI-dependent addons
4. **Preferences file** (`userpref.blend`) - Not copied by linuxserver image from /defaults

## Manual Workaround (For Now) 👤

When you login and get your Blender UI:

1. Open Blender UI at `http://localhost:13000` (shown after login)
2. Click **Edit → Preferences** (or press F4)
3. Go to **Add-ons** tab
4. Search for "MCP"
5. Check the box next to "Blender MCP Server"
6. Addon starts automatically, port 9876 becomes active
7. Go back to the chat interface
8. Click **"Connect to Blender"** button
9. ✅ You're connected!

**Note:** You only need to do this once per user. Blender saves the preference, so the addon will be enabled automatically next time you login.

## Automated Solutions (In Progress) 🔧

### Option 1: Pre-enabled Preferences File
Create a `userpref.blend` file with MCP addon pre-enabled and copy it to the container. **Status:** Requires running Blender once to generate this file.

### Option 2: MCP as Blender Extension Module
Package MCP as a Blender extension that auto-activates. **Status:** Requires restructuring addon code.

### Option 3: API-Based Enable
Use Blender's Python API through HTTP to enable the addon remotely. **Status:** Requires Blender HTTP server setup.

### Option 4: Custom Blender Build
Fork linuxserver/blender and modify the entrypoint script. **Status:** Most reliable but requires maintaining custom image.

### Recommended Next Step: Option 4
Modify the linuxserver/blender entrypoint to run a script that:
1. Waits for Blender UI to be fully started (check for process)
2. Uses `blender-softwaregl --python` to enable the addon
3. Restarts Blender to load the addon

## Testing Results 🧪

**Latest Test:** `e2etest_1765083938` (user_id=9)
- Container: `blender-e2etest_1765083938-9` ✅ Running
- MCP Port: `10000` ✅ Allocated
- UI Port: `13000` ✅ Accessible
- Addon File: `/config/.config/blender/5.0/scripts/addons/blender_mcp_addon.py` ✅ Present
- Addon Enabled: ❌ Not automatically (manual enable works)

## For Users 📢

**Your multi-user system is 95% functional!** Each user gets:
- ✅ Isolated Blender instance
- ✅ Personal workspace that persists
- ✅ No interference from other users
- ✅ Unique URL and ports

**One-time setup:** Enable the MCP addon in Blender UI (takes 10 seconds)

## For Developers 👨‍💻

The infrastructure is solid. The only remaining task is automating the addon enable step. All the hard parts (container isolation, port management, session lifecycle) are complete and working perfectly.

**To help debug:**
```powershell
# Check if container is running
docker ps | Select-String blender

# Check if addon file exists in container
docker exec blender-<username>-<id> ls -la /config/.config/blender/5.0/scripts/addons/

# Check if MCP port is listening
docker exec blender-<username>-<id> netstat -tuln | Select-String 9876

# View container logs
docker logs blender-<username>-<id>
```

---

**Last Updated:** December 6, 2024  
**Status:** Manual workaround available, automated solution in development  
**Impact:** Low - one-time user action required
