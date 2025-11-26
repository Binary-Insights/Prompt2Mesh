"""
Test Blender connection directly from Windows (no WSL forwarding needed)
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
    
    # Try to receive with 30s timeout
    sock.settimeout(30.0)
    chunks = []
    
    while True:
        try:
            chunk = sock.recv(8192)
            if not chunk:
                print("\n✗ Connection closed by server (no data)")
                break
            
            print(f"Received {len(chunk)} bytes")
            chunks.append(chunk)
            
            try:
                data = b''.join(chunks)
                response = json.loads(data.decode('utf-8'))
                print("\n" + "="*60)
                print("✓ SUCCESS! Got response:")
                print("="*60)
                print(json.dumps(response, indent=2))
                print("="*60)
                print("\n🎉 The addon is working correctly!")
                # return                ./setup_wsl_forward.sh                ./setup_wsl_forward.sh
                
            except json.JSONDecodeError:
                print("  (waiting for complete JSON...)")
                continue
                
        except socket.timeout:
            print("\n" + "="*60)
            print("✗ TIMEOUT - No response received after 30 seconds")
            print("="*60)
            if chunks:
                print(f"Partial data received: {b''.join(chunks)[:200]}")
            print("\nThis means the addon is still using the OLD code.")
            print("The threading.Event fix is NOT active.")
            break
            
except ConnectionRefusedError:
    print("\n✗ Connection refused!")
    print("Make sure Blender is running and the MCP server is started.")
    print("In Blender: BlenderMCP panel → 'Connect to Claude' button")
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
    
finally:
    sock.close()

print("\n" + "="*60)
print("NEXT STEPS:")
print("="*60)
print("If you got a timeout, the addon needs to be force-reloaded:")
print("")
print("Option 1 - Use Blender's Scripting Console:")
print("  1. In Blender: Switch to 'Scripting' workspace (top tabs)")
print("  2. In the Python Console (bottom), paste this:")
print("     import bpy")
print("     bpy.ops.blendermcp.stop_server()")
print("     bpy.ops.preferences.addon_disable(module='addon')")
print("     bpy.ops.preferences.addon_enable(module='addon')")
print("     bpy.ops.blendermcp.start_server()")
print("")
print("Option 2 - Manual addon removal:")
print("  1. Edit → Preferences → Add-ons")
print("  2. Search 'Blender MCP', click X to remove")
print("  3. Restart Blender")
print("  4. Reinstall addon, start server")
print("="*60)
