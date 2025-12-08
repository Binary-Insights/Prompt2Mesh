#!/bin/bash
# Simple test to check if we can connect to Blender from WSL

WINDOWS_IP=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}')
PORT=9876

echo "Testing connection to Blender..."
echo "Windows IP: $WINDOWS_IP"
echo "Port: $PORT"
echo ""

# Test with netcat/nc
if command -v nc &> /dev/null; then
    echo "Testing with netcat..."
    timeout 2 nc -zv $WINDOWS_IP $PORT 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Connection successful!"
    else
        echo "✗ Connection failed"
        echo ""
        echo "Possible solutions:"
        echo "1. Run this in PowerShell as Administrator:"
        echo "   New-NetFirewallRule -DisplayName 'Blender MCP WSL' -Direction Inbound -LocalPort 9876 -Protocol TCP -Action Allow"
        echo ""
        echo "2. Or use port forwarding:"
        echo "   ./setup_wsl_forward.sh"
    fi
else
    echo "netcat not found, installing..."
    sudo apt-get update && sudo apt-get install -y netcat
    echo "Run this script again after installation"
fi
