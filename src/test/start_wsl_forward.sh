#!/bin/bash
# Start the Python port forwarder for WSL
# This is more stable than socat

echo "Starting Python port forwarder..."
echo ""

# Kill any existing forwarders
pkill -f "wsl_port_forward.py" 2>/dev/null
sleep 1

# Start the Python forwarder in the background
python3 wsl_port_forward.py &

FORWARDER_PID=$!
echo ""
echo "Port forwarder started (PID: $FORWARDER_PID)"
echo ""
echo "To stop: kill $FORWARDER_PID"
echo "        or: pkill -f wsl_port_forward.py"
