#!/usr/bin/env python3
"""
Robust WSL to Windows port forwarder for Blender MCP
This runs in WSL and forwards localhost:9876 to Windows Blender server
"""
import socket
import threading
import time
import sys
import signal
import os

# Configuration
WSL_HOST = "127.0.0.1"
WSL_PORT = 9876

# Get Windows IP - try the actual WSL vEthernet interface first
def get_windows_host():
    # Try to get the default gateway (this is usually the WSL vEthernet interface)
    try:
        import subprocess
        result = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True
        )
        for line in result.stdout.splitlines():
            if "default via" in line:
                ip = line.split()[2]
                # Verify this IP actually works by testing connection
                import socket
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(1.0)
                try:
                    test_sock.connect((ip, 9876))
                    test_sock.close()
                    return ip
                except:
                    test_sock.close()
    except:
        pass
    
    # Fallback to resolv.conf
    return os.popen("cat /etc/resolv.conf | grep nameserver | awk '{print $2}'").read().strip()

WINDOWS_HOST = get_windows_host()
WINDOWS_PORT = 9876

# Global flag for clean shutdown
running = True

def handle_client(client_sock, client_addr):
    """Handle a single client connection by forwarding to Windows"""
    print(f"[{time.strftime('%H:%M:%S')}] New connection from {client_addr}")
    
    try:
        # Connect to Windows Blender server
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.settimeout(10.0)
        server_sock.connect((WINDOWS_HOST, WINDOWS_PORT))
        server_sock.settimeout(None)  # Remove timeout after connection
        client_sock.settimeout(None)  # Remove timeout on client too
        print(f"[{time.strftime('%H:%M:%S')}] Connected to Windows Blender at {WINDOWS_HOST}:{WINDOWS_PORT}")
        
        # Shared state to track when forwarding is complete
        forward_complete = threading.Event()
        active_directions = {'client_to_server': True, 'server_to_client': True}
        lock = threading.Lock()
        
        # Set up bidirectional forwarding
        def forward(source, destination, direction, direction_key):
            try:
                while running:
                    # Use blocking recv - no timeout unless connection is idle for very long
                    source.settimeout(300.0)  # 5 minute idle timeout
                    try:
                        data = source.recv(8192)
                    except socket.timeout:
                        # Connection idle for 5 minutes, close gracefully
                        print(f"[{time.strftime('%H:%M:%S')}] {direction}: Idle timeout (5 min)")
                        break
                        
                    if not data:
                        print(f"[{time.strftime('%H:%M:%S')}] {direction}: Connection closed")
                        break
                    
                    print(f"[{time.strftime('%H:%M:%S')}] {direction}: Forwarding {len(data)} bytes")
                    destination.sendall(data)
                    
            except Exception as e:
                if running:  # Only log if not shutting down
                    print(f"[{time.strftime('%H:%M:%S')}] {direction} error: {e}")
            finally:
                with lock:
                    active_directions[direction_key] = False
                    # Only shutdown if both directions are done
                    if not any(active_directions.values()):
                        forward_complete.set()
                print(f"[{time.strftime('%H:%M:%S')}] {direction}: Thread exiting")
        
        # Start forwarding threads
        client_to_server = threading.Thread(
            target=forward,
            args=(client_sock, server_sock, "Client→Server", "client_to_server"),
            daemon=True
        )
        server_to_client = threading.Thread(
            target=forward,
            args=(server_sock, client_sock, "Server→Client", "server_to_client"),
            daemon=True
        )
        
        client_to_server.start()
        server_to_client.start()
        
        # Wait for both threads to finish (with timeout)
        forward_complete.wait(timeout=60.0)
        
    except ConnectionRefusedError:
        print(f"[{time.strftime('%H:%M:%S')}] ✗ Windows Blender server not available at {WINDOWS_HOST}:{WINDOWS_PORT}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Error handling client: {e}")
    finally:
        try:
            client_sock.close()
        except:
            pass
        try:
            server_sock.close()
        except:
            pass
        print(f"[{time.strftime('%H:%M:%S')}] Connection from {client_addr} closed")

def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n[{time.strftime('%H:%M:%S')}] Shutting down...")
    running = False
    sys.exit(0)

def main():
    global running
    
    print("="*70)
    print("WSL → Windows Port Forwarder for Blender MCP")
    print("="*70)
    print(f"WSL Listening:    {WSL_HOST}:{WSL_PORT}")
    print(f"Windows Forward:  {WINDOWS_HOST}:{WINDOWS_PORT}")
    print("="*70)
    print("")
    
    # Set up signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create listening socket
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_sock.bind((WSL_HOST, WSL_PORT))
        server_sock.listen(5)
        print(f"✓ Port forwarder started successfully")
        print(f"  Listening on {WSL_HOST}:{WSL_PORT}")
        print(f"  Forwarding to {WINDOWS_HOST}:{WINDOWS_PORT}")
        print("")
        print("Now you can run from WSL:")
        print("  BLENDER_USE_LOCALHOST=1 python interactive_client.py")
        print("")
        print("Press Ctrl+C to stop")
        print("="*70)
        print("")
        
        # Accept connections
        while running:
            try:
                server_sock.settimeout(1.0)  # Allows checking 'running' flag
                try:
                    client_sock, client_addr = server_sock.accept()
                except socket.timeout:
                    continue
                    
                # Handle each client in a separate thread
                client_thread = threading.Thread(
                    target=handle_client,
                    args=(client_sock, client_addr),
                    daemon=True
                )
                client_thread.start()
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                if running:
                    print(f"[{time.strftime('%H:%M:%S')}] Server error: {e}")
                
    except OSError as e:
        print(f"✗ Failed to bind to {WSL_HOST}:{WSL_PORT}")
        print(f"  Error: {e}")
        print(f"\nMake sure no other process is using port {WSL_PORT}")
        print(f"Check with: lsof -i :{WSL_PORT}")
        return 1
    finally:
        server_sock.close()
        print(f"\n[{time.strftime('%H:%M:%S')}] Port forwarder stopped")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
