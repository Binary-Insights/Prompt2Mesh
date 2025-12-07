"""
Sculptor Agent - Image-to-3D Modeling Agent
Converts 2D images into 3D models using AI vision and Blender
"""
from .sculptor_agent import SculptorAgent, SculptorState, BlenderMCPConnection

__all__ = ["SculptorAgent", "SculptorState", "BlenderMCPConnection"]
__version__ = "1.0.0"
