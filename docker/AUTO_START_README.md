# Blender MCP Auto-Start Configuration

## Overview
The Blender MCP server now starts **automatically** when the Docker container starts. No manual intervention is required.

## How It Works

### 1. Container Startup Sequence
When the Blender Docker container starts:
```
1. LinuxServer.io base image initializes
2. S6-overlay runs init scripts in /etc/cont-init.d/
3. Our script (99-blender-mcp-startup) executes
4. Script waits for Blender to be ready
5. Blender MCP addon is enabled and server starts
```

### 2. Auto-Start Script (`blender_startup.sh`)
Located in the Docker container at `/etc/cont-init.d/99-blender-mcp-startup`

**Features:**
- Waits for Blender process to start (up to 120 seconds)
- Runs Blender in background mode to enable the addon
- Starts the MCP server on port 9876
- Logs all output to `/tmp/mcp_startup.log`
- Runs in background to not block container startup

### 3. Addon Enabler (`enable_addon_auto.py`)
Python script executed by Blender in background mode

**Features:**
- Verifies addon is installed
- Enables the addon persistently
- Saves preferences
- Starts the MCP server
- Comprehensive error handling and logging

## Configuration Files

### Modified Files
1. **docker-compose.yml**
   - Added mount: `./blender_startup.sh:/etc/cont-init.d/99-blender-mcp-startup:ro`
   - This places the startup script in S6-overlay's init directory

2. **blender_startup.sh** (NEW)
   - Main auto-start orchestration script
   - Waits for Blender, enables addon, starts server

3. **enable_addon_auto.py** (ENHANCED)
   - More robust addon detection
   - Better error handling
   - Persistent preference saving
   - Detailed logging

## Usage

### Starting the System
```bash
cd docker
docker compose up -d
```

**What happens:**
1. Containers start
2. Blender container initializes
3. Auto-start script runs in background
4. Within ~15-30 seconds, MCP server is ready
5. Backend can connect immediately

### Verifying Auto-Start

#### Check Startup Logs
```bash
docker exec prompt2mesh-blender cat /tmp/mcp_startup.log
```

#### Check MCP Server Status
```bash
# From another container (e.g., backend)
docker exec prompt2mesh-backend curl -v telnet://blender:9876
```

#### Check Container Logs
```bash
docker logs prompt2mesh-blender
```

### Manual Override (if needed)
If auto-start fails, you can still start manually:
1. Open Blender Web UI: http://localhost:3000
2. Edit > Preferences > Add-ons
3. Search "Blender MCP" and enable
4. View3D Sidebar (N key) > BlenderMCP tab
5. Click "Connect to Claude"

## Troubleshooting

### Server Not Starting Automatically

**Check init script execution:**
```bash
docker exec prompt2mesh-blender ls -la /etc/cont-init.d/
```

**Check startup log:**
```bash
docker exec prompt2mesh-blender cat /tmp/mcp_startup.log
```

**Check if Blender is running:**
```bash
docker exec prompt2mesh-blender pgrep -x blender
```

### Common Issues

1. **Addon not found**
   - Verify addon is mounted correctly:
     ```bash
     docker exec prompt2mesh-blender ls -la /config/.config/blender/5.0/scripts/addons/
     ```

2. **Server starts but stops**
   - Check for port conflicts
   - Verify firewall settings
   - Check Blender logs

3. **Script times out**
   - Increase wait time in `blender_startup.sh`
   - Check system resources (CPU/RAM)

## Benefits

### Before (Manual Start)
1. ❌ Start containers
2. ❌ Wait for Blender UI
3. ❌ Open web browser
4. ❌ Navigate to preferences
5. ❌ Enable addon
6. ❌ Click start server button
7. ✅ Backend can connect

### After (Auto Start)
1. ✅ Start containers
2. ✅ Backend connects automatically

**Time saved:** ~2-3 minutes per restart
**User actions required:** 0
**Error-prone manual steps eliminated:** 5

## Technical Details

### S6-Overlay Integration
The LinuxServer.io Blender image uses S6-overlay for process supervision. Scripts in `/etc/cont-init.d/` are executed during container initialization, numbered by filename (99- runs near the end).

### Background Execution
The script uses `&` and `wait` to run in the background, ensuring:
- Container startup isn't blocked
- MCP server starts asynchronously
- Docker health checks aren't affected

### Persistent Configuration
The addon is enabled with `persistent=True` and preferences are saved, ensuring:
- Addon stays enabled across restarts
- Server configuration persists
- No re-configuration needed

## Monitoring

### Health Check
Add to docker-compose.yml (optional):
```yaml
healthcheck:
  test: ["CMD", "nc", "-zv", "localhost", "9876"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

### Logging
All startup activity is logged to:
- `/tmp/mcp_startup.log` - Detailed addon enablement
- Container stdout - General progress

## Updating

If you modify the startup scripts:
```bash
# Restart just the Blender container
docker compose restart blender

# Or rebuild and restart
docker compose up -d --force-recreate blender
```

No code changes needed - scripts are mounted as volumes!

## Security Notes

- Scripts are mounted as read-only (`:ro`)
- No sensitive data in startup scripts
- Server only accessible within Docker network
- Port 9876 not exposed to host by default

## Support

If auto-start fails:
1. Check logs: `/tmp/mcp_startup.log`
2. Verify addon file exists and is readable
3. Ensure sufficient startup time
4. Try manual enable to test addon functionality
5. Check Docker resource limits

---

**Status:** ✅ Fully Automated
**Tested:** Docker Compose v3.8+
**Platform:** Linux containers (WSL2, native Linux)
