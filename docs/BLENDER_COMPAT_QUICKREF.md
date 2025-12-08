# Blender Compatibility Quick Reference

## 🔴 Common Errors & Quick Fixes

### Error 1: "Node type ShaderNodeTexMusgrave undefined"
```python
# ❌ FAILS in Blender 4.x+
musgrave = nodes.new(type='ShaderNodeTexMusgrave')

# ✅ FIX: Use compatibility helper
musgrave = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Name', (x, y))
```

### Error 2: "KeyError: 'Specular'" or "KeyError: 'Emission'"
```python
# ❌ FAILS in Blender 4.x+
bsdf.inputs['Specular'].default_value = 0.5
bsdf.inputs['Emission'].default_value = (1, 1, 1, 1)

# ✅ FIX: Use compatibility helper
set_principled_bsdf_property(bsdf, 'Specular', 0.5)
set_principled_bsdf_property(bsdf, 'Emission', (1, 1, 1, 1))
```

---

## 📋 Property Name Mapping (Blender 3.x → 4.x)

| Old Name | New Name (Blender 4.x+) |
|----------|------------------------|
| `Specular` | `Specular IOR` or `Specular IOR Level` |
| `Emission` | `Emission Color` |

---

## 🔄 Node Type Replacements

| Removed in 4.0 | Replacement | Helper Function |
|---------------|-------------|-----------------|
| `ShaderNodeTexMusgrave` | `ShaderNodeTexNoise` (with FBM type) | `create_texture_node()` |

---

## ✅ Safe Properties (Work in All Versions)

These properties can be accessed directly without helpers:

```python
# Safe to use directly
bsdf.inputs['Base Color'].default_value = (r, g, b, 1.0)
bsdf.inputs['Roughness'].default_value = 0.5
bsdf.inputs['Metallic'].default_value = 0.0
bsdf.inputs['Subsurface'].default_value = 0.1
bsdf.inputs['Subsurface Color'].default_value = (r, g, b, 1.0)
bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.5, 0.25)
bsdf.inputs['Normal'].default_value = (0, 0, 1)
bsdf.inputs['Alpha'].default_value = 1.0
```

---

## 📦 Include These Helpers in Every Script

```python
import bpy

def set_principled_bsdf_property(bsdf, property_name, value):
    """Set BSDF property with version compatibility"""
    property_mapping = {
        'Specular': 'Specular IOR',
        'Emission': 'Emission Color',
    }
    try:
        bsdf.inputs[property_name].default_value = value
        return True
    except KeyError:
        mapped_name = property_mapping.get(property_name)
        if mapped_name:
            try:
                bsdf.inputs[mapped_name].default_value = value
                return True
            except KeyError:
                pass
    return False

def create_texture_node(node_tree, node_type, name, location):
    """Create texture node with Blender 4.x compatibility"""
    if node_type == 'ShaderNodeTexMusgrave':
        node = node_tree.nodes.new(type='ShaderNodeTexNoise')
        node.name = name
        node.location = location
        if hasattr(node, 'noise_type'):
            node.noise_type = 'FBM'
        return node
    else:
        node = node_tree.nodes.new(type=node_type)
        node.name = name
        node.location = location
        return node
```

---

## 🎯 Decision Tree: When to Use Helpers?

```
Are you setting a BSDF property?
├─ Yes → Is it 'Specular' or 'Emission'?
│  ├─ Yes → ✅ Use set_principled_bsdf_property()
│  └─ No → ✅ Direct access is fine
└─ No → Are you creating a texture node?
   ├─ Yes → Is it Musgrave?
   │  ├─ Yes → ✅ Use create_texture_node()
   │  └─ No → ✅ Direct nodes.new() is fine
   └─ No → ✅ No helper needed
```

---

## 🚀 Quick Start Template

```python
import bpy

# Include compatibility helpers (copy from above)
def set_principled_bsdf_property(bsdf, property_name, value):
    # ... implementation ...
    pass

def create_texture_node(node_tree, node_type, name, location):
    # ... implementation ...
    pass

# Your code starts here
mat = bpy.data.materials.new(name="MyMaterial")
mat.use_nodes = True
nodes = mat.node_tree.nodes
bsdf = nodes.get("Principled BSDF")

# Safe: Works in all versions
bsdf.inputs['Base Color'].default_value = (0.8, 0.5, 0.3, 1.0)
bsdf.inputs['Roughness'].default_value = 0.7

# Use helper: Version-sensitive
set_principled_bsdf_property(bsdf, 'Specular', 0.5)

# Use helper: Node creation
grain = create_texture_node(nodes, 'ShaderNodeTexMusgrave', 'Grain', (-1200, -200))
grain.inputs['Scale'].default_value = 50.0
```

---

## 📖 Full Documentation

For complete details, see `BLENDER_COMPATIBILITY.md`
