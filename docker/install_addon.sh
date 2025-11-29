#!/bin/bash
# Blender MCP Addon Auto-Installation Script
# This script automatically enables the addon when Blender starts

BLENDER_VERSION="5.0"
ADDON_DIR="/config/.config/blender/${BLENDER_VERSION}/scripts/addons"
ADDON_FILE="blender_mcp_addon.py"
STARTUP_SCRIPT="/config/.config/blender/${BLENDER_VERSION}/scripts/startup/enable_mcp.py"

echo "==================================================="
echo "Blender MCP Addon Installation Script"
echo "==================================================="

# Wait for Blender config directory to be created
echo "Waiting for Blender config directory..."
while [ ! -d "/config/.config/blender/${BLENDER_VERSION}" ]; do
    sleep 2
done

echo "✓ Blender config directory found"

# Create addons directory if it doesn't exist
mkdir -p "${ADDON_DIR}"
mkdir -p "/config/.config/blender/${BLENDER_VERSION}/scripts/startup"

echo "✓ Created addon directories"

# Check if addon file exists
if [ -f "${ADDON_DIR}/${ADDON_FILE}" ]; then
    echo "✓ Addon file is mounted at: ${ADDON_DIR}/${ADDON_FILE}"
else
    echo "⚠ Warning: Addon file not found at ${ADDON_DIR}/${ADDON_FILE}"
    echo "  Make sure addon.py is in the project root"
fi

# Create a startup script to enable the addon automatically
cat > "${STARTUP_SCRIPT}" << 'EOF'
import bpy
import sys

def enable_blender_mcp():
    """Enable Blender MCP addon on startup"""
    addon_name = "blender_mcp_addon"
    
    # Check if addon is already enabled
    if addon_name in bpy.context.preferences.addons:
        print(f"✓ {addon_name} is already enabled")
        return
    
    # Try to enable the addon
    try:
        bpy.ops.preferences.addon_enable(module=addon_name)
        bpy.ops.wm.save_userpref()
        print(f"✓ Successfully enabled {addon_name}")
    except Exception as e:
        print(f"⚠ Failed to enable {addon_name}: {e}")
        print(f"  Available addons: {list(bpy.context.preferences.addons.keys())}")

# Run on startup
if __name__ != "__main__":
    # Delay execution to ensure Blender is fully initialized
    bpy.app.timers.register(enable_blender_mcp, first_interval=2.0)
EOF

echo "✓ Created startup script to enable addon"

echo "==================================================="
echo "Installation Complete!"
echo "==================================================="
echo ""
echo "The Blender MCP addon will be automatically enabled when Blender starts."
echo "Access Blender at: http://localhost:3000"
echo ""
echo "To verify the addon:"
echo "  1. Open Blender web UI (http://localhost:3000)"
echo "  2. Go to Edit > Preferences > Add-ons"
echo "  3. Search for 'Blender MCP'"
echo "  4. The addon should be enabled"
echo ""
echo "To use the addon:"
echo "  1. Press 'N' in the 3D viewport to show the sidebar"
echo "  2. Click on the 'BlenderMCP' tab"
echo "  3. Click 'Connect to Claude'"
echo "==================================================="
