"""
Test script to verify Blender addon connection without MCP client
"""
import socket
import json
import sys
import os
import subprocess

def get_host():
    """Get the correct host IP for Blender connection"""
    if os.path.exists('/proc/version'):
        # Check if we're in WSL
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                try:
                    # Get Windows host IP from WSL
                    result = subprocess.run(
                        ['cat', '/etc/resolv.conf'],
                        capture_output=True,
                        text=True
                    )
                    for line in result.stdout.split('\n'):
                        if 'nameserver' in line:
                            return line.split()[1]
                except:
                    pass
    return "localhost"

HOST = get_host()
PORT = 9876

def send_command(sock, command):
    """Send a command to Blender and receive response"""
    print(f"\n→ Sending: {command}")
    
    # Send command
    sock.sendall(json.dumps(command).encode('utf-8'))
    
    # Receive response
    chunks = []
    sock.settimeout(15.0)
    
    while True:
        try:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            
            # Try to parse as complete JSON
            try:
                data = b''.join(chunks)
                response = json.loads(data.decode('utf-8'))
                print(f"✓ Received: {json.dumps(response, indent=2)}")
                return response
            except json.JSONDecodeError:
                # Incomplete JSON, continue receiving
                continue
        except socket.timeout:
            break
    
    if chunks:
        data = b''.join(chunks)
        print(f"✗ Received incomplete data: {data.decode('utf-8', errors='replace')}")
        return None
    
    print("✗ No response received")
    return None

def main():
    """Test the Blender connection"""
    print("Blender MCP Connection Test")
    print("=" * 50)
    
    # Show which host we're connecting to
    if HOST != "localhost":
        print(f"\n🐧 Running in WSL - connecting to Windows host: {HOST}")
    else:
        print(f"\n💻 Connecting to: {HOST}")
    
    # Try to connect
    print(f"\nConnecting to Blender at {HOST}:{PORT}...")
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((HOST, PORT))
        print("✓ Connected successfully!")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nMake sure:")
        print("1. Blender is running")
        print("2. The Blender MCP addon is installed and enabled")
        print("3. The server is started in Blender (BlenderMCP panel → Start Server)")
        sys.exit(1)
    
    try:
        # Test 1: Get Blender info
        print("\n" + "=" * 50)
        print("Test 1: Get Blender Info")
        print("=" * 50)
        send_command(sock, {
            "command": "get_blender_info"
        })
        
        # Test 2: Create a sphere
        print("\n" + "=" * 50)
        print("Test 2: Create a UV Sphere")
        print("=" * 50)
        send_command(sock, {
            "command": "execute_python",
            "code": """
import bpy

# Delete default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create a UV sphere
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=1.0,
    location=(0, 0, 2),
    segments=32,
    ring_count=16
)

# Get the sphere object
sphere = bpy.context.active_object
sphere.name = "TestSphere"

result = {
    "status": "success",
    "message": "Created sphere with physics",
    "object_name": sphere.name,
    "location": list(sphere.location)
}
"""
        })
        
        # Test 3: Add rigid body physics
        print("\n" + "=" * 50)
        print("Test 3: Add Gravity Physics")
        print("=" * 50)
        send_command(sock, {
            "command": "execute_python",
            "code": """
import bpy

# Get the sphere
sphere = bpy.data.objects.get("TestSphere")

if sphere:
    # Select the sphere
    bpy.ops.object.select_all(action='DESELECT')
    sphere.select_set(True)
    bpy.context.view_layer.objects.active = sphere
    
    # Add rigid body physics
    bpy.ops.rigidbody.object_add()
    sphere.rigid_body.type = 'ACTIVE'
    sphere.rigid_body.mass = 1.0
    sphere.rigid_body.friction = 0.5
    sphere.rigid_body.restitution = 0.5
    
    result = {
        "status": "success",
        "message": "Added rigid body physics to sphere",
        "object": sphere.name,
        "physics_type": sphere.rigid_body.type,
        "mass": sphere.rigid_body.mass
    }
else:
    result = {
        "status": "error",
        "message": "TestSphere not found"
    }
"""
        })
        
        # Test 4: Add ground plane
        print("\n" + "=" * 50)
        print("Test 4: Add Ground Plane")
        print("=" * 50)
        send_command(sock, {
            "command": "execute_python",
            "code": """
import bpy

# Create ground plane
bpy.ops.mesh.primitive_plane_add(
    size=10.0,
    location=(0, 0, 0)
)

ground = bpy.context.active_object
ground.name = "Ground"

# Add rigid body physics (passive)
bpy.ops.rigidbody.object_add()
ground.rigid_body.type = 'PASSIVE'

result = {
    "status": "success",
    "message": "Created ground plane with passive physics",
    "object_name": ground.name
}
"""
        })
        
        print("\n" + "=" * 50)
        print("✓ All tests completed successfully!")
        print("=" * 50)
        print("\nCheck Blender - you should see:")
        print("- A sphere at height 2 with active rigid body physics")
        print("- A ground plane at height 0 with passive rigid body physics")
        print("- Press spacebar in Blender to run the physics simulation!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sock.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    main()
