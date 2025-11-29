#!/bin/bash
# Auto-enable Blender MCP addon and start server on container startup

# Wait for Blender to be fully started
echo "Waiting for Blender to start..."
sleep 10

# Enable the addon by adding it to Blender's config
BLENDER_PREFS="/config/.config/blender/5.0/config/userpref.blend"
ADDON_SCRIPT="/tmp/enable_addon_auto.py"

# Check if Blender is running
if pgrep -x "blender" > /dev/null; then
    echo "Blender is running, attempting to enable MCP addon..."
    
    # Run the Python script in Blender's background mode
    blender --background --python "$ADDON_SCRIPT" 2>&1 | tee /tmp/addon_enable.log
    
    echo "Addon auto-enable script executed"
    echo "Check /tmp/addon_enable.log for details"
else
    echo "Blender is not running yet. Please enable the addon manually from the UI:"
    echo "1. Open Blender Web UI at http://localhost:3000"
    echo "2. Go to Edit > Preferences > Add-ons"
    echo "3. Search for 'Blender MCP'"
    echo "4. Enable the checkbox"
    echo "5. Go to View3D > Sidebar (N key) > BlenderMCP tab"
    echo "6. Click 'Connect to Claude' button"
fi
