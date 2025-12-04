# Blender Version Compatibility Guide

## Overview

This project is designed to work with **Blender 4.x and 5.x**. Due to API changes between Blender versions, we've implemented compatibility helpers to ensure smooth operation across different versions.

---

## Breaking Changes in Blender 4.0+

### 1. Principled BSDF Property Renames

**Blender 3.x → 4.x Changes:**

| Old Property Name | New Property Name (Blender 4.x+) |
|------------------|----------------------------------|
| `Specular` | `Specular IOR` or `Specular IOR Level` |
| `Emission` | `Emission Color` |

**Problem:**
```python
# ❌ This fails in Blender 4.x
bsdf.inputs['Specular'].default_value = 0.5
```

**Solution:**
```python
# ✅ Use the compatibility helper
set_principled_bsdf_property(bsdf, 'Specular', 0.5)
```

### 2. Musgrave Texture Node Removed

**Status:** `ShaderNodeTexMusgrave` was **REMOVED** in Blender 4.0

**Replacement:** Enhanced `ShaderNodeTexNoise` with multiple noise types

**Problem:**
```python
# ❌ This fails in Blender 4.x
musgrave = nodes.new(type='ShaderNodeTexMusgrave')
```

**Solution:**
```python
# ✅ Use the compatibility helper
musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Fine_Grain', (-1200, -200))
# Automatically converts to ShaderNodeTexNoise with FBM type in Blender 4.x+
```

### 3. Noise Texture Enhancements

**Blender 4.0+ Noise Types:**
- `FBM` (Fractal Brownian Motion) - Approximates old Musgrave behavior
- `MULTI_FRACTAL`
- `RIDGED_MULTIFRACTAL`
- `PERLIN`
- `VORONOI`

**Migration:**
```python
# Blender 3.x Musgrave
musgrave = nodes.new(type='ShaderNodeTexMusgrave')
musgrave.musgrave_type = 'RIDGED_MULTIFRACTAL'

# Blender 4.x+ Equivalent
noise = nodes.new(type='ShaderNodeTexNoise')
noise.noise_type = 'FBM'  # Or 'RIDGED_MULTIFRACTAL'
```

---

## Compatibility Helper Functions

### Function 1: `set_principled_bsdf_property()`

**Purpose:** Set BSDF properties with automatic version detection

**Signature:**
```python
def set_principled_bsdf_property(bsdf, property_name, value) -> bool
```

**Parameters:**
- `bsdf`: Principled BSDF node
- `property_name`: Property name (e.g., 'Specular', 'Emission')
- `value`: Value to set (float or tuple)

**Returns:** `True` if successful, `False` otherwise

**Example:**
```python
import bpy

# Get material
mat = bpy.data.materials.get("Wood")
bsdf = mat.node_tree.nodes.get("Principled BSDF")

# Set properties with version compatibility
set_principled_bsdf_property(bsdf, 'Specular', 0.5)
set_principled_bsdf_property(bsdf, 'Emission', (1.0, 0.8, 0.6, 1.0))
```

### Function 2: `create_texture_node()`

**Purpose:** Create texture nodes with Blender 4.x compatibility

**Signature:**
```python
def create_texture_node(node_tree, node_type, name, location) -> bpy.types.Node
```

**Parameters:**
- `node_tree`: Shader node tree
- `node_type`: Node type string (e.g., 'ShaderNodeTexMusgrave')
- `name`: Node name
- `location`: Tuple (x, y) for node position

**Returns:** Created node (automatically converted if needed)

**Example:**
```python
import bpy

mat = bpy.data.materials.get("Wood")
nodes = mat.node_tree

# Create Musgrave-like texture (works in all versions)
musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Fine_Grain', (-1200, -200))
musgrave.inputs['Scale'].default_value = 50.0

# In Blender 3.x: Creates ShaderNodeTexMusgrave
# In Blender 4.x: Creates ShaderNodeTexNoise with FBM type
```

---

## Common Migration Patterns

### Pattern 1: Material Setup with BSDF

```python
import bpy

# Get or create material
mat = bpy.data.materials.new(name="WoodMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links

# Get Principled BSDF
bsdf = nodes.get("Principled BSDF")

# Set basic properties (work in all versions)
bsdf.inputs['Base Color'].default_value = (0.8, 0.5, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.7
bsdf.inputs['Metallic'].default_value = 0.0

# Set version-sensitive properties (use helper)
set_principled_bsdf_property(bsdf, 'Specular', 0.5)
set_principled_bsdf_property(bsdf, 'Emission', (0.0, 0.0, 0.0, 1.0))
```

### Pattern 2: Procedural Texture Setup

```python
import bpy

mat = bpy.data.materials.get("Wood")
nodes = mat.node_tree
links = mat.node_tree.links

# Texture coordinate
tex_coord = nodes.new(type='ShaderNodeTexCoord')
tex_coord.location = (-1600, 0)

# Noise texture (safe in all versions)
noise = nodes.new(type='ShaderNodeTexNoise')
noise.location = (-1200, 100)
noise.inputs['Scale'].default_value = 15.0

# Musgrave-like texture (use helper for compatibility)
musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Fine_Grain', (-1200, -200))
musgrave.inputs['Scale'].default_value = 50.0

# Link textures
links.new(tex_coord.outputs['Generated'], noise.inputs['Vector'])
links.new(tex_coord.outputs['Generated'], musgrave.inputs['Vector'])
```

### Pattern 3: Complete Wood Material

```python
import bpy

def create_wood_material_compatible():
    """Create wood material compatible with Blender 4.x and 5.x"""
    
    # Create material
    mat = bpy.data.materials.new(name="Wood_Oak")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    
    # Clear default nodes
    nodes.clear()
    
    # Output node
    output = nodes.new(type='ShaderNodeOutputMaterial')
    output.location = (300, 0)
    
    # Principled BSDF
    bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
    bsdf.location = (0, 0)
    
    # Texture coordinate
    tex_coord = nodes.new(type='ShaderNodeTexCoord')
    tex_coord.location = (-1600, 0)
    
    # Base color texture
    color_noise = nodes.new(type='ShaderNodeTexNoise')
    color_noise.location = (-1200, 200)
    color_noise.inputs['Scale'].default_value = 15.0
    
    # Fine grain detail (use helper)
    grain = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Grain', (-1200, -200))
    grain.inputs['Scale'].default_value = 50.0
    
    # Color ramp for variation
    color_ramp = nodes.new(type='ShaderNodeValToRGB')
    color_ramp.location = (-800, 200)
    color_ramp.color_ramp.elements[0].color = (0.6, 0.4, 0.2, 1.0)
    color_ramp.color_ramp.elements[1].color = (0.8, 0.6, 0.4, 1.0)
    
    # Link nodes
    links.new(tex_coord.outputs['Generated'], color_noise.inputs['Vector'])
    links.new(tex_coord.outputs['Generated'], grain.inputs['Vector'])
    links.new(color_noise.outputs['Fac'], color_ramp.inputs['Fac'])
    links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
    links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    
    # Set BSDF properties (use helpers for compatibility)
    bsdf.inputs['Roughness'].default_value = 0.7
    bsdf.inputs['Metallic'].default_value = 0.0
    set_principled_bsdf_property(bsdf, 'Specular', 0.5)
    
    return mat

# Use the function
wood_material = create_wood_material_compatible()
```

---

## Troubleshooting

### Error: "Node type ShaderNodeTexMusgrave undefined"

**Cause:** Running Blender 4.x+ which removed Musgrave Texture

**Solution:** Use `create_texture_node()` helper instead of direct `nodes.new()`

```python
# ❌ Direct creation fails
musgrave = nodes.new(type='ShaderNodeTexMusgrave')

# ✅ Use helper
musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Grain', (-1200, -200))
```

### Error: "KeyError: 'Specular'"

**Cause:** Property renamed in Blender 4.x

**Solution:** Use `set_principled_bsdf_property()` helper

```python
# ❌ Direct access fails in Blender 4.x
bsdf.inputs['Specular'].default_value = 0.5

# ✅ Use helper
set_principled_bsdf_property(bsdf, 'Specular', 0.5)
```

### Error: "AttributeError: 'ShaderNodeTexNoise' object has no attribute 'musgrave_type'"

**Cause:** Trying to set Musgrave-specific properties on Noise node

**Solution:** Check node type before setting properties

```python
# Create node with helper
node = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Grain', (-1200, -200))

# Check actual node type before setting properties
if node.type == 'TEX_MUSGRAVE':
    node.musgrave_type = 'RIDGED_MULTIFRACTAL'
elif node.type == 'TEX_NOISE':
    if hasattr(node, 'noise_type'):
        node.noise_type = 'FBM'
```

---

## Testing Compatibility

### Test Script

```python
import bpy

def test_blender_compatibility():
    """Test compatibility helpers"""
    
    # Create test material
    mat = bpy.data.materials.new(name="CompatibilityTest")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    
    # Test 1: BSDF property setting
    bsdf = nodes.get("Principled BSDF")
    try:
        set_principled_bsdf_property(bsdf, 'Specular', 0.5)
        print("✅ BSDF property setting works")
    except Exception as e:
        print(f"❌ BSDF property setting failed: {e}")
    
    # Test 2: Musgrave texture creation
    try:
        musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Test', (0, 0))
        print(f"✅ Texture creation works (created {musgrave.type})")
    except Exception as e:
        print(f"❌ Texture creation failed: {e}")
    
    # Cleanup
    bpy.data.materials.remove(mat)
    print("\nCompatibility test complete!")

# Run test
test_blender_compatibility()
```

---

## Best Practices

1. **Always use compatibility helpers** when:
   - Setting BSDF properties (`Specular`, `Emission`)
   - Creating Musgrave textures

2. **Direct access is safe** for:
   - Basic BSDF properties (`Base Color`, `Roughness`, `Metallic`)
   - Standard texture nodes (`ShaderNodeTexNoise`, `ShaderNodeTexImage`)

3. **Include compatibility code** at the start of all Blender Python scripts:
   ```python
   import bpy
   
   # Include compatibility helpers here
   def set_principled_bsdf_property(bsdf, property_name, value):
       # ... (full implementation)
   
   def create_texture_node(node_tree, node_type, name, location):
       # ... (full implementation)
   ```

4. **Test across versions** if possible:
   - Blender 3.6 LTS (for legacy compatibility)
   - Blender 4.2 LTS (current stable)
   - Blender 5.0+ (latest features)

---

## Additional Resources

- [Blender 4.0 Release Notes](https://wiki.blender.org/wiki/Reference/Release_Notes/4.0)
- [Blender Python API Documentation](https://docs.blender.org/api/current/)
- [Shader Nodes API Reference](https://docs.blender.org/api/current/bpy.types.ShaderNode.html)

---

## Summary

The Artisan Agent automatically handles Blender version differences by:

1. ✅ **Auto-detecting** which Blender version is running
2. ✅ **Converting** deprecated nodes (Musgrave → Noise)
3. ✅ **Mapping** renamed properties (Specular → Specular IOR)
4. ✅ **Providing** fallback mechanisms for maximum compatibility

**No manual intervention required** - the system handles everything automatically!
