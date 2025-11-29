# Blender Addon Installation in Docker

## Automatic Installation (Recommended)

The Blender MCP addon is automatically installed when you start the Docker containers.

### How It Works

1. **Addon Mounting**: The `addon.py` file is mounted into the Blender container at:
   ```
   /config/.config/blender/4.2/scripts/addons/blender_mcp_addon.py
   ```

2. **Auto-Enable**: A startup script automatically enables the addon when Blender starts.

3. **Persistent Config**: The addon configuration is stored in the `blender_config` Docker volume.

### Usage

1. **Start the containers:**
   ```bash
   cd docker
   docker-compose up -d
   ```

2. **Access Blender Web UI:**
   - Open browser: http://localhost:3000
   - Default password: `abc` (if prompted)

3. **Verify addon is installed:**
   - In Blender: Edit > Preferences > Add-ons
   - Search for "Blender MCP"
   - Should be enabled automatically

4. **Use the addon:**
   - Press `N` in 3D viewport to show sidebar
   - Click "BlenderMCP" tab
   - Configure settings:
     - Port: 9876 (default)
     - Enable Poly Haven assets (optional)
     - Enable Hyper3D Rodin (optional)
     - Enable Sketchfab (optional)
   - Click "Connect to Claude"

## Manual Installation (Alternative)

If automatic installation doesn't work, you can install manually:

### Option 1: Through Blender UI

1. Access Blender at http://localhost:3000
2. Go to Edit > Preferences > Add-ons
3. Click "Install"
4. Navigate to the mounted addon file (already available in the container)
5. Click "Install Add-on from File"
6. Enable the "Blender MCP" addon

### Option 2: Docker Exec

```bash
# Copy addon to Blender container
docker cp addon.py prompt2mesh-blender:/config/.config/blender/4.2/scripts/addons/blender_mcp_addon.py

# Restart Blender container
docker-compose restart blender
```

## Troubleshooting

### Addon Not Showing Up

1. **Check if file is mounted:**
   ```bash
   docker exec prompt2mesh-blender ls -la /config/.config/blender/4.2/scripts/addons/
   ```

2. **Check Blender version:**
   The path uses Blender 4.2. If you have a different version, update the path in `docker-compose.yml`:
   ```yaml
   - ../addon.py:/config/.config/blender/[YOUR_VERSION]/scripts/addons/blender_mcp_addon.py:ro
   ```

3. **Restart container:**
   ```bash
   docker-compose restart blender
   ```

### Addon Not Enabled

1. **Run installation script:**
   ```bash
   docker exec prompt2mesh-blender /install_addon.sh
   ```

2. **Enable manually in Blender UI:**
   - Edit > Preferences > Add-ons
   - Search "Blender MCP"
   - Check the checkbox

### Check Logs

```bash
# View Blender container logs
docker-compose logs blender

# Follow logs in real-time
docker-compose logs -f blender
```

## Addon Configuration

The addon provides several features:

### 1. Poly Haven Assets
- Enable in addon settings: "Use assets from Poly Haven"
- Free HDRIs, textures, and models
- No API key required

### 2. Hyper3D Rodin
- Enable in addon settings: "Use Hyper3D Rodin 3D model generation"
- Choose platform: hyper3d.ai or fal.ai
- Add API key (free trial available)

### 3. Sketchfab
- Enable in addon settings: "Use assets from Sketchfab"
- Requires API key (get from sketchfab.com)

### 4. Tencent Hunyuan 3D
- Enable in addon settings: "Use Tencent Hunyuan 3D model generation"
- Choose mode: Local API or Official API
- Configure API endpoint

## Updating the Addon

To update the addon code:

1. **Edit addon.py** in your project root
2. **Restart Blender container:**
   ```bash
   docker-compose restart blender
   ```
3. **Reload addon in Blender:**
   - Disable and re-enable in Add-ons preferences
   - Or restart Blender application

## Docker Volume Persistence

The addon configuration is stored in the `blender_config` volume, which persists across container restarts:

```bash
# List volumes
docker volume ls | grep blender

# Inspect volume
docker volume inspect prompt2mesh_blender_config

# Remove volume (will reset all Blender settings)
docker volume rm prompt2mesh_blender_config
```

## Integration with Backend

The addon communicates with the FastAPI backend:

1. **Addon** runs Blender MCP server on port 9876
2. **Backend** connects to Blender via socket connection
3. **Streamlit** sends requests through backend

Make sure all three containers are running:
```bash
docker-compose ps
```

Expected output:
```
NAME                      STATUS
prompt2mesh-backend       Up
prompt2mesh-blender       Up
prompt2mesh-streamlit     Up
prompt2mesh-postgres      Up
```

## Port Configuration

- **Blender Web UI**: http://localhost:3000
- **Blender VNC**: localhost:3001
- **Backend API**: http://localhost:8000
- **Streamlit UI**: http://localhost:8501
- **Blender MCP Server**: Port 9876 (internal)

## Security Notes

1. The addon file is mounted as **read-only** (`:ro`)
2. Default credentials should be changed in production
3. API keys should be stored in environment variables
4. The Blender container runs as user `abc` (non-root)

## Next Steps

After installation:

1. **Connect backend to Blender:**
   - Start backend: `docker-compose up backend`
   - Backend will auto-connect to Blender MCP server

2. **Use Streamlit interface:**
   - Open http://localhost:8501
   - Login with credentials (root/root)
   - Access Artisan Agent page
   - Start chatting with Blender!

3. **Test the connection:**
   - In Artisan Agent page, click "Connect to Blender"
   - Try a simple prompt: "Create a red cube"
   - View results in Blender Web UI (http://localhost:3000)
