"""Clear Blender scene via MCP connection"""
import asyncio
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

async def main():
    from blender_mcp.connection import BlenderMCPConnection
    
    print("Connecting to Blender MCP...")
    conn = BlenderMCPConnection()
    await conn.connect()
    
    print("Clearing all objects...")
    result = await conn.call_tool('execute_blender_code', {
        'code': '''
import bpy
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False, confirm=False)

# Clean orphaned data
for mesh in bpy.data.meshes:
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for mat in bpy.data.materials:
    if mat.users == 0:
        bpy.data.materials.remove(mat)

print(f"Scene cleared. Remaining: {len(bpy.data.objects)} objects")
'''
    })
    
    print(f"Result: {result}")
    
    await conn.close()
    print("✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
