"""
Interactive Blender MCP Client
A simple CLI client to send natural language commands to Blender
"""
import socket
import json
import sys
import os
import subprocess
from typing import Dict, Any

# Detect if running in WSL and get Windows host IP
def get_host():
    """Get the correct host IP for Blender connection"""
    # Check if BLENDER_USE_LOCALHOST env var is set (for port forwarding)
    if os.getenv('BLENDER_USE_LOCALHOST', '').lower() in ['1', 'true', 'yes']:
        return "localhost"
    
    if os.path.exists('/proc/version'):
        # Check if we're in WSL
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                # Check if socat port forwarding is running
                try:
                    result = subprocess.run(
                        ['pgrep', '-f', 'socat.*:9876'],
                        capture_output=True,
                        text=True
                    )
                    if result.returncode == 0:
                        # Port forwarding is active, use localhost
                        return "localhost"
                except:
                    pass
                
                # No port forwarding, get Windows host IP
                try:
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
PORT = int(os.getenv('BLENDER_PORT', '9876'))  # Allow override via environment variable

class BlenderClient:
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.sock = None
        
    def connect(self) -> bool:
        """Connect to Blender addon"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((self.host, self.port))
            print(f"✓ Connected to Blender at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            print("\nMake sure:")
            print("1. Blender is running")
            print("2. The Blender MCP addon is installed and enabled")
            print("3. The server is started (BlenderMCP panel → Start Server)")
            return False
    
    def disconnect(self):
        """Disconnect from Blender"""
        if self.sock:
            self.sock.close()
            self.sock = None
    
    def send_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to Blender and get response"""
        if not self.sock:
            return {"status": "error", "message": "Not connected"}
        
        try:
            # Send command
            self.sock.sendall(json.dumps(command).encode('utf-8'))
            
            # Receive response
            chunks = []
            self.sock.settimeout(15.0)
            
            while True:
                try:
                    chunk = self.sock.recv(8192)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    
                    # Try to parse as complete JSON
                    try:
                        data = b''.join(chunks)
                        response = json.loads(data.decode('utf-8'))
                        return response
                    except json.JSONDecodeError:
                        continue
                except socket.timeout:
                    break
            
            if chunks:
                data = b''.join(chunks)
                return {"status": "error", "message": f"Incomplete response: {data.decode('utf-8', errors='replace')}"}
            
            return {"status": "error", "message": "No response received"}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    def execute_python(self, code: str) -> Dict[str, Any]:
        """Execute Python code in Blender"""
        return self.send_command({
            "type": "execute_code",
            "params": {
                "code": code
            }
        })

def create_sphere_with_physics():
    """Generate code to create a sphere with gravity physics"""
    return """
import bpy

# Delete default objects if present
if len(bpy.data.objects) > 0:
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

# Create UV sphere
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=1.0,
    location=(0, 0, 5),
    segments=32,
    ring_count=16
)

sphere = bpy.context.active_object
sphere.name = "PhysicsSphere"

# Add rigid body physics
bpy.ops.rigidbody.object_add()
sphere.rigid_body.type = 'ACTIVE'
sphere.rigid_body.mass = 1.0
sphere.rigid_body.friction = 0.5
sphere.rigid_body.restitution = 0.8  # Bouncy

# Create ground plane
bpy.ops.mesh.primitive_plane_add(
    size=20.0,
    location=(0, 0, 0)
)

ground = bpy.context.active_object
ground.name = "Ground"

# Add passive rigid body to ground
bpy.ops.rigidbody.object_add()
ground.rigid_body.type = 'PASSIVE'

# Add a camera
bpy.ops.object.camera_add(location=(7, -7, 5))
camera = bpy.context.active_object
camera.rotation_euler = (1.1, 0, 0.785)
bpy.context.scene.camera = camera

# Add a light
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
light = bpy.context.active_object
light.data.energy = 2.0

result = {
    "status": "success",
    "message": "Created sphere with gravity physics, ground plane, camera, and light",
    "sphere": sphere.name,
    "ground": ground.name,
    "sphere_location": list(sphere.location),
    "instructions": "Press SPACEBAR in Blender to run the physics simulation!"
}
"""

def create_bouncing_cubes():
    """Generate code to create multiple bouncing cubes"""
    return """
import bpy
import random

# Clear scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create ground
bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.name = "Ground"
bpy.ops.rigidbody.object_add()
ground.rigid_body.type = 'PASSIVE'

# Create 5 cubes at different heights
cubes = []
for i in range(5):
    x = random.uniform(-3, 3)
    y = random.uniform(-3, 3)
    z = random.uniform(3, 8)
    
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x, y, z))
    cube = bpy.context.active_object
    cube.name = f"Cube_{i+1}"
    
    # Add physics
    bpy.ops.rigidbody.object_add()
    cube.rigid_body.type = 'ACTIVE'
    cube.rigid_body.mass = random.uniform(0.5, 2.0)
    cube.rigid_body.restitution = random.uniform(0.3, 0.9)
    
    # Random color
    mat = bpy.data.materials.new(name=f"Material_{i+1}")
    mat.use_nodes = True
    mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (
        random.random(), random.random(), random.random(), 1.0
    )
    cube.data.materials.append(mat)
    
    cubes.append(cube.name)

result = {
    "status": "success",
    "message": "Created 5 bouncing cubes with random colors",
    "cubes": cubes,
    "instructions": "Press SPACEBAR to run physics!"
}
"""

def main():
    """Interactive Blender client"""
    print("=" * 60)
    print("Blender MCP Interactive Client")
    print("=" * 60)
    
    # Show which host we're connecting to
    if HOST == "localhost":
        # Check if we're in WSL
        if os.path.exists('/proc/version'):
            with open('/proc/version', 'r') as f:
                if 'microsoft' in f.read().lower():
                    print(f"\n🐧 WSL → Using port forwarding to localhost:{PORT}")
                else:
                    print(f"\n💻 Connecting to: {HOST}:{PORT}")
        else:
            print(f"\n💻 Connecting to: {HOST}:{PORT}")
    else:
        print(f"\n🐧 Running in WSL - connecting to Windows host: {HOST}:{PORT}")
    
    client = BlenderClient()
    
    if not client.connect():
        sys.exit(1)
    
    print("\nCommands:")
    print("  1 - Create sphere with gravity physics")
    print("  2 - Create bouncing cubes")
    print("  custom - Enter custom Python code")
    print("  info - Get Blender info")
    print("  quit - Exit")
    print()
    
    try:
        while True:
            command = input("\n→ Enter command: ").strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            elif command == '1':
                print("Creating sphere with gravity physics...")
                code = create_sphere_with_physics()
                response = client.execute_python(code)
                print(json.dumps(response, indent=2))
            
            elif command == '2':
                print("Creating bouncing cubes...")
                code = create_bouncing_cubes()
                response = client.execute_python(code)
                print(json.dumps(response, indent=2))
            
            elif command == 'info':
                print("Getting Blender info...")
                response = client.send_command({
                    "type": "get_scene_info",
                    "params": {}
                })
                print(json.dumps(response, indent=2))
            
            elif command == 'custom':
                print("\nEnter Python code (type 'END' on a new line to finish):")
                lines = []
                while True:
                    line = input()
                    if line.strip() == 'END':
                        break
                    lines.append(line)
                
                code = '\n'.join(lines)
                if code.strip():
                    print("\nExecuting custom code...")
                    response = client.execute_python(code)
                    print(json.dumps(response, indent=2))
            
            else:
                print(f"Unknown command: {command}")
    
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    finally:
        client.disconnect()
        print("Disconnected from Blender")

if __name__ == "__main__":
    main()
