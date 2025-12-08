"""Clear all objects from Blender scene"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from blender_mcp.connection import BlenderMCPConnection

async def main():
    """Clear Blender scene"""
    print("Connecting to Blender MCP server...")
    
    connection = BlenderMCPConnection()
    await connection.connect()
    
    print("Clearing all objects from scene...")
    
    result = await connection.call_tool("execute_blender_code", {
        "code": """
import bpy

# Select all objects
bpy.ops.object.select_all(action='SELECT')

# Delete all selected objects
bpy.ops.object.delete(use_global=False, confirm=False)

# Also remove any orphaned data
for mesh in bpy.data.meshes:
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
        
for mat in bpy.data.materials:
    if mat.users == 0:
        bpy.data.materials.remove(mat)

print(f"Scene cleared. Remaining objects: {len(bpy.data.objects)}")
"""
    })
    
    print(f"Result: {result}")
    
    # Verify scene is empty
    scene_info = await connection.call_tool("get_scene_info", {})
    print(f"Scene info: {scene_info}")
    
    await connection.close()
    print("✅ Scene cleared successfully")

if __name__ == "__main__":
    asyncio.run(main())
