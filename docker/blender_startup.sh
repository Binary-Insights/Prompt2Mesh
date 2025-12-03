#!/bin/bash
# Blender MCP Auto-Start Script
# This script runs in the background and automatically enables/starts the MCP server

echo "🚀 Blender MCP Auto-Start Script initialized..."

# Function to check if Blender is ready
wait_for_blender() {
    echo "⏳ Waiting for Blender to be ready..."
    MAX_ATTEMPTS=60
    ATTEMPT=0
    
    while [ $ATTEMPT -lt $MAX_ATTEMPTS ]; do
        # Check if Blender process is running
        if pgrep -x "blender" > /dev/null 2>&1; then
            echo "✅ Blender process detected"
            # Give it a few more seconds to fully initialize
            sleep 5
            return 0
        fi
        
        ATTEMPT=$((ATTEMPT + 1))
        echo "⏳ Waiting for Blender... ($ATTEMPT/$MAX_ATTEMPTS)"
        sleep 2
    done
    
    echo "❌ Blender did not start within expected time"
    return 1
}

# Function to enable addon and start MCP server
enable_mcp_server() {
    echo "🔧 Enabling Blender MCP addon and starting server..."
    
    # Python script to run in Blender
    PYTHON_SCRIPT="/tmp/enable_addon_auto.py"
    
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        echo "❌ Auto-enable script not found: $PYTHON_SCRIPT"
        return 1
    fi
    
    # Run Blender in background with the Python script
    # Use --factory-startup to avoid loading user preferences that might interfere
    blender --background --python "$PYTHON_SCRIPT" > /tmp/mcp_startup.log 2>&1
    
    # Check if successful
    if [ $? -eq 0 ]; then
        echo "✅ MCP addon enabled and server started"
        echo "📋 Startup log saved to /tmp/mcp_startup.log"
        return 0
    else
        echo "❌ Failed to enable MCP addon. Check /tmp/mcp_startup.log for details"
        cat /tmp/mcp_startup.log
        return 1
    fi
}

# Main execution
main() {
    echo "=================================="
    echo "🎨 Blender MCP Auto-Start"
    echo "=================================="
    
    # Wait for Blender to be ready
    if wait_for_blender; then
        # Give Blender GUI a bit more time to stabilize
        echo "⏳ Waiting for Blender GUI to stabilize..."
        sleep 10
        
        # Enable addon and start server
        if enable_mcp_server; then
            echo ""
            echo "=================================="
            echo "🎉 Blender MCP is ready!"
            echo "=================================="
            echo "📍 MCP Server: blender:9876"
            echo "🌐 Blender Web UI: http://localhost:3000"
            echo ""
        else
            echo ""
            echo "=================================="
            echo "⚠️  MCP Auto-Start Failed"
            echo "=================================="
            echo "Please enable manually:"
            echo "1. Open Blender Web UI at http://localhost:3000"
            echo "2. Edit > Preferences > Add-ons"
            echo "3. Search 'Blender MCP' and enable"
            echo "4. View3D Sidebar (N) > BlenderMCP > Connect"
            echo ""
        fi
    else
        echo "⚠️  Could not detect Blender startup"
    fi
}

# Run in background to not block container startup
main &

# Keep script running so Docker doesn't think the process ended
wait
