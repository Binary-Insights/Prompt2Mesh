"""
Verify the Blender addon has the fix
"""
import socket
import json
import time

HOST = "localhost"
PORT = 9876

print(f"Connecting to {HOST}:{PORT}...")
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.settimeout(5.0)

try:
    sock.connect((HOST, PORT))
    print("✓ Connected!")
    
    # Send command
    command = {"type": "get_scene_info", "params": {}}
    print(f"\nSending: {json.dumps(command)}")
    sock.sendall(json.dumps(command).encode('utf-8'))
    
    print("Waiting for response...")
    time.sleep(2)  # Give it time
    
    # Try to receive
    sock.settimeout(30.0)
    chunks = []
    
    while True:
        try:
            chunk = sock.recv(8192)
            if not chunk:
                print("Connection closed by server (no data)")
                break
            
            print(f"Received {len(chunk)} bytes")
            chunks.append(chunk)
            
            try:
                data = b''.join(chunks)
                response = json.loads(data.decode('utf-8'))
                print("\n✓ SUCCESS! Got response:")
                print(json.dumps(response, indent=2))
                break
            except json.JSONDecodeError:
                print("  (waiting for complete JSON...)")
                continue
                
        except socket.timeout:
            print("\n✗ Timeout - no response received")
            if chunks:
                print(f"Partial data: {b''.join(chunks)[:200]}")
            break
            
except Exception as e:
    print(f"✗ Error: {e}")
finally:
    sock.close()

print("\n" + "="*60)
print("If you see 'Connection closed by server (no data)', the addon")
print("was not properly reloaded. Try these steps:")
print("1. In Blender: Edit → Preferences → Add-ons")
print("2. Find 'Blender MCP' and click the X to remove it")
print("3. Restart Blender completely")
print("4. Reinstall the addon from:")
print("   C:\\Users\\enigm\\AppData\\Roaming\\Blender Foundation\\Blender\\4.5\\scripts\\addons\\addon.py")
print("5. Start the server again")
print("="*60)
