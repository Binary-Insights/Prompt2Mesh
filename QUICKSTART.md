# Prompt2Mesh Quick Reference

## TL;DR - Get Started in 3 Steps

### Step 1: Start Blender Server
```
1. Open Blender
2. Edit → Preferences → Add-ons → Install → Select addon.py
3. Enable "Blender MCP" checkbox
4. Press N in 3D View → BlenderMCP tab → Start Server
```

### Step 2: Run Interactive Client
```bash
cd Prompt2Mesh

# From Windows PowerShell:
python interactive_client.py

# From WSL:
python interactive_client.py  # Auto-detects WSL and connects to Windows host
```

### Step 3: Create Something!
```
→ Enter command: 1  # Creates sphere with physics
```

Then press **SPACEBAR** in Blender to see the physics!

---

## What Each File Does

| File | Purpose |
|------|---------|
| `addon.py` | Blender addon - runs inside Blender |
| `main.py` | MCP server - for MCP clients (Claude, Cline) |
| `interactive_client.py` | ⭐ **Use this for testing!** |
| `test_blender_connection.py` | Automated test suite |

---

## Common Commands (interactive_client.py)

```
1           Create sphere with gravity
2           Create 5 bouncing cubes with random colors
custom      Write your own Python code
info        Get Blender version info
quit        Exit
```

---

## Example Custom Commands

### Create a Cube
```python
import bpy
bpy.ops.mesh.primitive_cube_add(location=(0, 0, 0))
result = {"status": "success", "message": "Cube created"}
```

### Change Object Color
```python
import bpy
obj = bpy.context.active_object
mat = bpy.data.materials.new(name="Red")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0, 0, 1)
obj.data.materials.append(mat)
result = {"status": "success", "message": "Set to red"}
```

### Render Scene
```python
import bpy
bpy.context.scene.render.filepath = "/tmp/render.png"
bpy.ops.render.render(write_still=True)
result = {"status": "success", "message": "Rendered to /tmp/render.png"}
```

---

## Architecture

```
┌──────────────┐
│   Blender    │  ← You see the 3D scene here
│   + Addon    │  ← Server running on port 9876
└──────┬───────┘
       │ TCP Socket
       ↓
┌──────────────┐
│ interactive_ │  ← Use this for testing!
│  client.py   │  ← Sends Python commands
└──────────────┘

       OR

┌──────────────┐
│   main.py    │  ← MCP Server (for Claude, Cline)
│  (MCP Server)│  ← Translates MCP → Blender
└──────┬───────┘
       │ stdio (JSON-RPC)
       ↓
┌──────────────┐
│ MCP Client   │  ← Claude Desktop, Cline, etc.
│ (Claude/etc) │
└──────────────┘
```

---

## Troubleshooting

| Error | Solution |
|-------|----------|
| Connection refused | Start server in Blender (BlenderMCP panel) |
| Connection refused (WSL) | Scripts auto-detect WSL and use Windows host IP |
| Invalid JSON | Don't type into main.py - use interactive_client.py |
| Port in use | Stop/restart server in Blender |
| Module not found | Activate virtual environment (.venv) |

---

## Pro Tips

1. **Always** start the Blender server first
2. Use `interactive_client.py` for quick testing
3. Press **SPACEBAR** in Blender to run physics simulations
4. All Python code must set a `result` variable (dict with status/message)
5. Check Blender's system console for errors (Window → Toggle System Console)

---

## Next Steps

- See `SETUP_GUIDE.md` for MCP client configuration
- See `test_blender_connection.py` for more examples
- Explore the Blender Python API: https://docs.blender.org/api/current/
