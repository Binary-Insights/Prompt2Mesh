"""Clear all objects from Blender scene"""
import socket
import json
import sys

HOST = "blender"  # Docker service name
PORT = 9876

def send_command(sock, command):
    """Send command and get response"""
    sock.sendall(json.dumps(command).encode('utf-8'))
    
    chunks = []
    sock.settimeout(10.0)
    
    while True:
        try:
            chunk = sock.recv(8192)
            if not chunk:
                break
            chunks.append(chunk)
            
            try:
                data = b''.join(chunks)
                return json.loads(data.decode('utf-8'))
            except json.JSONDecodeError:
                continue
        except socket.timeout:
            break
    
    return None

def main():
    print("Connecting to Blender...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))
    print("✓ Connected")
    
    print("\nClearing all objects...")
    response = send_command(sock, {
        "command": "execute_python",
        "code": """
import bpy

# Select all objects
bpy.ops.object.select_all(action='SELECT')

# Delete all
bpy.ops.object.delete(use_global=False, confirm=False)

# Clean up orphaned data
for mesh in bpy.data.meshes:
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
        
for mat in bpy.data.materials:
    if mat.users == 0:
        bpy.data.materials.remove(mat)

result = {
    "status": "success",
    "objects_remaining": len(bpy.data.objects),
    "message": "Scene cleared"
}
"""
    })
    
    print(f"Response: {response}")
    
    sock.close()
    print("\n✅ Scene cleared successfully")

if __name__ == "__main__":
    main()
