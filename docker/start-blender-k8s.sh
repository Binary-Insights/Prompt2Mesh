#!/bin/bash
set -e

echo "Starting Blender services for Kubernetes..."

# Create Docker marker file so addon auto-start detects container environment
touch /.dockerenv

# Copy addon files to the mounted /config volume
echo "Installing Blender MCP addon..."
mkdir -p /config/.config/blender/5.0/scripts/addons/blender_mcp
cp -r /tmp/blender_mcp_addon/* /config/.config/blender/5.0/scripts/addons/blender_mcp/

# Install startup script to auto-start MCP server when GUI launches
echo "Installing MCP auto-start script..."
mkdir -p /config/.config/blender/5.0/scripts/startup
cp /tmp/mcp_autostart.py /config/.config/blender/5.0/scripts/startup/

chown -R abc:abc /config/.config/blender

# Start the base linuxserver/blender init system in background
# This starts Xorg, nginx, selkies (web UI), etc.
/init &

# Wait for services to start
echo "Waiting for web UI services to start..."
sleep 10

# Check if nginx is running (serves the web UI)
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo "Web UI is ready on port 3000"
        break
    fi
    echo "Waiting for web UI... ($i/30)"
    sleep 2
done

# Enable Blender addon by modifying userpref.blend
echo "Enabling Blender MCP addon..."

# Set BLENDER_USER_SCRIPTS so Blender finds our addon
export BLENDER_USER_SCRIPTS="/config/.config/blender/5.0/scripts"

# Create a Python script to enable addon and save preferences
cat > /tmp/enable_addon.py << 'EOF'
import bpy
import sys

# Enable the addon
try:
    bpy.ops.preferences.addon_enable(module='blender_mcp')
    # Save user preferences so addon stays enabled
    bpy.ops.wm.save_userpref()
    print("✅ Blender MCP addon enabled and saved successfully")
except Exception as e:
    print(f"❌ Failed to enable addon: {e}")
    sys.exit(1)
EOF

# Run Blender in background to enable addon (run as abc user to use correct config)
su abc -c "BLENDER_USER_SCRIPTS=/config/.config/blender/5.0/scripts blender --background --python /tmp/enable_addon.py" 2>&1 | grep -E "addon|Error|Failed|✅|❌" || true

echo "✅ Blender addon enabled and will start when Blender GUI opens"
echo "📝 MCP server will connect automatically when addon starts"

# Keep container running
echo "All services started. Container ready."
tail -f /dev/null
