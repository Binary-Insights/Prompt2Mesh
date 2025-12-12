#!/bin/bash
# WSL Port Forwarding Script for Blender MCP
# This creates a port forward from WSL to Windows Blender server

WINDOWS_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
WSL_PORT=9876
WINDOWS_PORT=9876

echo "Setting up port forwarding from WSL to Windows Blender..."
echo "Windows IP: $WINDOWS_IP"

# Kill any existing socat processes on this port
pkill -f "socat.*:$WSL_PORT" 2>/dev/null

# Check if socat is installed
if ! command -v socat &> /dev/null; then
    echo "Installing socat..."
    sudo apt-get update && sudo apt-get install -y socat
fi

# Create port forward
echo "Forwarding localhost:$WSL_PORT -> $WINDOWS_IP:$WINDOWS_PORT"
socat TCP-LISTEN:$WSL_PORT,fork,reuseaddr TCP:$WINDOWS_IP:$WINDOWS_PORT &

SOCAT_PID=$!
echo "Port forwarding active (PID: $SOCAT_PID)"
echo ""
echo "Now run the interactive client with:"
echo "  BLENDER_USE_LOCALHOST=1 python interactive_client.py"
echo ""
echo "To stop forwarding: kill $SOCAT_PID"
