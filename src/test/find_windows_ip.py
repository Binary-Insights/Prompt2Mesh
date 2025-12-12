#!/usr/bin/env python3
"""Quick test - try connecting to different Windows IPs"""
import socket

IPS_TO_TRY = [
    "172.24.96.1",  # WSL vEthernet interface
    "10.255.255.254",  # resolv.conf nameserver
    "127.0.0.1",  # localhost (should work via wsl_port_forward.py)
]

PORT = 9876

for ip in IPS_TO_TRY:
    print(f"Trying {ip}:{PORT}...", end=" ")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    try:
        sock.connect((ip, PORT))
        print(f"✓ SUCCESS!")
        sock.close()
        print(f"\nUse this IP: {ip}")
        break
    except Exception as e:
        print(f"✗ {type(e).__name__}")
    finally:
        sock.close()
