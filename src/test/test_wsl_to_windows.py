#!/usr/bin/env python3
"""
Test direct connection from WSL to Windows Blender
"""
import socket
import sys
import os
import subprocess

# Try to get the actual WSL host IP (vEthernet interface on Windows)
def get_windows_ip():
    # First try the WSL vEthernet interface IP
    try:
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True
        )
        # Extract the gateway IP from "default via X.X.X.X"
        for line in result.stdout.splitlines():
            if "default via" in line:
                return line.split()[2]
    except:
        pass
    
    # Fallback to resolv.conf
    return os.popen("cat /etc/resolv.conf | grep nameserver | awk '{print $2}'").read().strip()

WINDOWS_IP = get_windows_ip()
PORT = 9876

print(f"Testing connection to Windows Blender at {WINDOWS_IP}:{PORT}")
print("="*60)

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5.0)

try:
    print(f"Attempting to connect...")
    sock.connect((WINDOWS_IP, PORT))
    print(f"✓ SUCCESS! Connected to {WINDOWS_IP}:{PORT}")
    print(f"  Socket: {sock.getsockname()} -> {sock.getpeername()}")
    sock.close()
    print("\nWindows Blender is reachable from WSL!")
    sys.exit(0)
    
except ConnectionRefusedError:
    print(f"✗ Connection REFUSED by {WINDOWS_IP}:{PORT}")
    print("\nPossible causes:")
    print("1. Windows Firewall is blocking WSL connections")
    print("2. Blender server not running or not listening on 0.0.0.0")
    sys.exit(1)
    
except socket.timeout:
    print(f"✗ Connection TIMEOUT to {WINDOWS_IP}:{PORT}")
    print("\nPossible causes:")
    print("1. Windows Firewall is silently dropping packets")
    print("2. Network routing issue between WSL and Windows")
    sys.exit(1)
    
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
