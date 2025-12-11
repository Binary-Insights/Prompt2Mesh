"""
Sculptor Agent - Image-to-3D Modeling Agent for Blender
Analyzes 2D images and autonomously creates 3D models using LangGraph
"""
import os
import sys
import json
import base64
import asyncio
import traceback
from io import BytesIO
from typing import TypedDict, Annotated, Sequence, List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langsmith import traceable

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.errors import GraphRecursionError

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Configure LangSmith
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "true"

# Rate limit configuration
RATE_LIMIT_MAX_RETRIES = int(os.getenv("RATE_LIMIT_MAX_RETRIES", "5"))
RATE_LIMIT_BASE_WAIT = int(os.getenv("RATE_LIMIT_BASE_WAIT", "15"))
RATE_LIMIT_STEP_DELAY = float(os.getenv("RATE_LIMIT_STEP_DELAY", "2.0"))


# Rate limit handling
async def invoke_with_retry(model, messages, max_retries=None, base_wait=None):
    """Invoke LLM with exponential backoff for rate limits"""
    if max_retries is None:
        max_retries = RATE_LIMIT_MAX_RETRIES
    if base_wait is None:
        base_wait = RATE_LIMIT_BASE_WAIT
        
    for attempt in range(max_retries):
        try:
            return await model.ainvoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "rate_limit" in error_str or "429" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = base_wait * (2 ** attempt)
                print(f"⏳ Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                await asyncio.sleep(wait_time)
            else:
                raise


def invoke_with_retry_sync(model, messages, max_retries=None, base_wait=None):
    """Synchronous version of invoke_with_retry"""
    if max_retries is None:
        max_retries = RATE_LIMIT_MAX_RETRIES
    if base_wait is None:
        base_wait = RATE_LIMIT_BASE_WAIT
        
    for attempt in range(max_retries):
        try:
            return model.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "rate_limit" in error_str or "429" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                wait_time = base_wait * (2 ** attempt)
                print(f"⏳ Rate limit hit, waiting {wait_time}s (attempt {attempt + 1}/{max_retries})...")
                import time
                time.sleep(wait_time)
            else:
                raise


# Blender Version Compatibility Helper
BLENDER_COMPAT_CODE = '''
# Blender 4.x/5.x compatibility helper
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
    """Create texture node with Blender 4.x/5.x compatibility"""
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

def set_boolean_solver(modifier, solver_type='FAST'):
    """Set Boolean modifier solver with version compatibility"""
    # Blender 4.x renamed/removed 'FAST' solver
    # Valid options: 'EXACT', 'FLOAT' (Blender 4.x+), 'MANIFOLD' (Blender 5.x+)
    solver_mapping = {
        'FAST': 'FLOAT',  # FAST was removed, use FLOAT instead
        'EXACT': 'EXACT',  # Still valid
        'FLOAT': 'FLOAT',  # Blender 4.x+
    }
    
    target_solver = solver_mapping.get(solver_type, 'FLOAT')
    
    try:
        # Try setting the solver
        modifier.solver = target_solver
        return True
    except:
        # Fallback to EXACT if FLOAT isn't available
        try:
            modifier.solver = 'EXACT'
            return True
        except:
            return False

def create_material_with_color(obj, mat_name, color=(1.0, 0.0, 0.0, 1.0), roughness=0.5, metallic=0.0):
    """
    Safe material creation with error handling
    Creates a material with specified color and applies it to object
    
    Args:
        obj: Blender object to apply material to
        mat_name: Name for the material
        color: RGBA tuple (red, green, blue, alpha) - values 0.0 to 1.0
        roughness: Roughness value 0.0 to 1.0
        metallic: Metallic value 0.0 to 1.0
    
    Returns:
        Material object or None if failed
    """
    try:
        # Validate object has data attribute (mesh, curve, etc.)
        if not hasattr(obj, 'data'):
            print(f"Error: Object {obj.name if hasattr(obj, 'name') else 'unknown'} has no data attribute")
            return None
        
        # Create material
        mat = bpy.data.materials.get(mat_name)
        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
        
        # Enable nodes
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        
        # Get or create Principled BSDF
        bsdf = nodes.get("Principled BSDF")
        if bsdf is None:
            # Clear default nodes and create fresh
            nodes.clear()
            bsdf = nodes.new(type='ShaderNodeBsdfPrincipled')
            output = nodes.new(type='ShaderNodeOutputMaterial')
            output.location = (300, 0)
            mat.node_tree.links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
        
        # Set properties safely
        if 'Base Color' in bsdf.inputs:
            bsdf.inputs['Base Color'].default_value = color
        if 'Roughness' in bsdf.inputs:
            bsdf.inputs['Roughness'].default_value = roughness
        if 'Metallic' in bsdf.inputs:
            bsdf.inputs['Metallic'].default_value = metallic
        
        # Apply material to object - check if materials slot exists
        if hasattr(obj.data, 'materials'):
            if len(obj.data.materials) > 0:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)
        else:
            print(f"Warning: Object {obj.name} does not support materials")
            return None
        
        return mat
        
    except AttributeError as e:
        print(f"Material creation error - AttributeError: {e}")
        print(f"Object type: {type(obj).__name__}")
        return None
    except Exception as e:
        print(f"Material creation error: {e}")
        return None

def get_or_create_material(mat_name):
    """Safely get existing material or create new one"""
    mat = bpy.data.materials.get(mat_name)
    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
    return mat
'''


class SculptorState(TypedDict):
    """State of the Sculptor Agent"""
    messages: Annotated[Sequence[BaseMessage], "Conversation messages"]
    session_id: str
    screenshot_dir: Path
    input_image_path: str  # Path to input 2D image
    input_image_base64: str  # Base64 encoded input image
    input_image_media_type: str  # MIME type of input image (e.g., image/jpeg, image/png)
    reference_image_base64: Optional[str]  # Reference image in Blender scene
    tool_results: List[Dict[str, Any]]
    screenshot_count: int
    planning_steps: List[str]  # Dynamically generated steps
    current_step: int
    is_complete: bool
    feedback_history: List[str]
    vision_analysis: str  # Initial analysis of input image
    current_modeling_phase: str  # "planning", "base_structure", "details", "refinement", "complete"
    needs_replanning: bool  # Whether to regenerate steps based on progress
    quality_scores: List[Dict[str, Any]]
    critical_error: Optional[str]
    max_replanning_attempts: int
    replanning_count: int


class BlenderMCPConnection:
    """Manages connection to Blender MCP server"""
    
    def __init__(self):
        self.mcp_session = None
        self.tools: Dict[str, Any] = {}
        self.stdio_context = None
        self.session_context = None
        self._cleanup_done = False
    
    @traceable(name="initialize_blender_mcp")
    async def initialize(self) -> int:
        """Initialize MCP connection to Blender"""
        env = os.environ.copy()
        
        server_params = StdioServerParameters(
            command="python",
            args=["main.py"],
            env=env
        )
        
        self.stdio_context = stdio_client(server_params)
        read, write = await self.stdio_context.__aenter__()
        
        self.session_context = ClientSession(read, write)
        self.mcp_session = await self.session_context.__aenter__()
        
        tools_list = await self.mcp_session.list_tools()
        self.tools = {tool.name: tool for tool in tools_list.tools}
        
        return len(self.tools)
    
    @traceable(name="call_blender_tool")
    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Call a Blender MCP tool"""
        try:
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            if result.isError:
                return {
                    "success": False,
                    "error": str(result.content)
                }
            
            content_text = ""
            if hasattr(result, 'content') and result.content:
                for item in result.content:
                    if hasattr(item, 'text'):
                        content_text += item.text
            
            return {
                "success": True,
                "result": content_text
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self._cleanup_done:
            return
        
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.stdio_context:
                await self.stdio_context.__aexit__(None, None, None)
        except Exception:
            pass
        finally:
            self._cleanup_done = True
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get tools in LangChain format"""
        tools_schema = []
        for tool_name, tool in self.tools.items():
            tools_schema.append({
                "name": tool_name,
                "description": tool.description or f"Tool: {tool_name}",
                "parameters": tool.inputSchema
            })
        return tools_schema


class SculptorAgent:
    """
    Image-to-3D modeling agent that:
    1. Analyzes input 2D image
    2. Dynamically plans modeling steps
    3. Executes steps using Blender MCP
    4. Takes screenshots and compares with input
    5. Replans if needed
    6. Iterates until 3D model matches input image
    """
    
    def __init__(self, session_id: Optional[str] = None, display_callback: Optional[callable] = None, cancellation_check: Optional[callable] = None, mcp_connection: Optional[BlenderMCPConnection] = None):
        """
        Initialize the Sculptor Agent
        
        Args:
            session_id: Optional session ID
            display_callback: Optional callback for displaying progress
            cancellation_check: Optional callback that returns True if cancelled
            mcp_connection: Optional existing MCP connection to share (avoids duplicate connections)
        """
        self.session_id = session_id or str(uuid4())
        self.display_callback = display_callback or self._console_display
        self.cancellation_check = cancellation_check or (lambda: False)
        
        # Initialize LLMs - separate models for vision and reasoning
        self.vision_model = ChatAnthropic(
            model=os.getenv("CLAUDE_VISION_MODEL", "claude-sonnet-4-20250514"),
            temperature=0.3,
            max_tokens=1024,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        self.reasoning_model = ChatAnthropic(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Use shared MCP connection or create new one
        self.mcp = mcp_connection if mcp_connection else BlenderMCPConnection()
        self.owns_mcp = mcp_connection is None  # Track if we own the connection
        
        # Memory for conversation history
        self.memory = MemorySaver()
        
        # Create LangGraph workflow
        self.graph = None
    
    def _console_display(self, message: str, type: str = "info"):
        """Default console display"""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "tool": "🔧",
            "plan": "📋",
            "screenshot": "📸",
            "thinking": "🤔",
            "vision": "👁️"
        }
        print(f"{icons.get(type, '•')} {message}")
    
    def _trim_message_history(self, messages: List[BaseMessage], max_messages: int = 10) -> List[BaseMessage]:
        """
        Trim message history to prevent context overflow
        Keep first message (vision analysis) and most recent messages
        
        Args:
            messages: List of messages
            max_messages: Maximum number of messages to keep
            
        Returns:
            Trimmed list of messages
        """
        if len(messages) <= max_messages:
            return messages
        
        # Always keep the first message (vision analysis)
        first_message = messages[0] if messages else None
        
        # Keep the most recent messages
        recent_messages = messages[-(max_messages - 1):]
        
        if first_message:
            return [first_message] + recent_messages
        else:
            return recent_messages
    
    @traceable(name="initialize_sculptor_agent")
    async def initialize(self):
        """Initialize the agent and Blender connection"""
        self.display_callback("Initializing Sculptor Agent...", "info")
        
        # Connect to Blender only if we own the connection
        if self.owns_mcp:
            num_tools = await self.mcp.initialize()
            self.display_callback(f"Connected to Blender MCP ({num_tools} tools available)", "success")
        else:
            # Using shared connection
            num_tools = len(self.mcp.tools)
            self.display_callback(f"Using shared Blender MCP connection ({num_tools} tools available)", "success")
        
        # Create workflow
        self.graph = self._create_graph()
        self.display_callback("LangGraph workflow created", "success")
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow with dynamic planning"""
        workflow = StateGraph(SculptorState)
        
        # Add nodes
        workflow.add_node("analyze_input_image", self._analyze_input_image_node)
        workflow.add_node("load_reference_image", self._load_reference_image_node)
        workflow.add_node("plan_steps", self._plan_steps_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("capture_feedback", self._capture_feedback_node)
        workflow.add_node("assess_progress", self._assess_progress_node)
        workflow.add_node("complete", self._complete_node)
        
        # Set entry point
        workflow.set_entry_point("analyze_input_image")
        
        # Add edges
        workflow.add_edge("analyze_input_image", "load_reference_image")
        workflow.add_edge("load_reference_image", "plan_steps")
        workflow.add_edge("plan_steps", "execute_step")
        workflow.add_edge("execute_step", "capture_feedback")
        workflow.add_edge("capture_feedback", "assess_progress")
        
        # Conditional edge: replan, continue, or complete
        workflow.add_conditional_edges(
            "assess_progress",
            self._should_continue,
            {
                "replan": "plan_steps",
                "continue": "execute_step",
                "complete": "complete"
            }
        )
        
        workflow.add_edge("complete", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    @traceable(name="analyze_input_image")
    async def _analyze_input_image_node(self, state: SculptorState) -> SculptorState:
        """Analyze the input 2D image to understand what needs to be modeled"""
        self.display_callback("Analyzing input image with vision model...", "vision")
        
        # Create vision prompt
        vision_prompt = f"""You are analyzing a 2D image that needs to be recreated as a 3D model in Blender.

Analyze this image and provide:

1. **Main Objects**: What are the primary objects/subjects in the image?
2. **Shapes and Forms**: Describe the basic geometric shapes (cubes, spheres, cylinders, etc.)
3. **Spatial Relationships**: How are objects positioned relative to each other?
4. **Colors and Materials**: What SPECIFIC colors do you see? (Provide RGB estimates or color names)
   - List each visible object and its color
   - Identify material types (metallic, plastic, fabric, glass, etc.)
   - Note any textures, patterns, or surface details
5. **Details and Features**: What specific details or features are important?
6. **Complexity Level**: Rate the modeling complexity (simple/medium/complex)
7. **Suggested Approach**: What modeling strategy would work best?

**CRITICAL**: Be very specific about colors. The 3D model MUST have matching colors, not default gray materials.
Example: "Red sphere (RGB ~1.0, 0.0, 0.0)", "Blue metallic cylinder (RGB ~0.2, 0.5, 1.0, metallic=0.8)"

Be specific and technical. This analysis will be used to plan the 3D modeling steps.
"""
        
        # Create message with image
        messages = [
            HumanMessage(
                content=[
                    {"type": "text", "text": vision_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{state['input_image_media_type']};base64,{state['input_image_base64']}"
                        }
                    }
                ]
            )
        ]
        
        try:
            response = await invoke_with_retry(self.vision_model, messages)
            analysis = response.content
            
            self.display_callback(f"Image analysis complete: {len(analysis)} chars", "success")
            
            state["vision_analysis"] = analysis
            state["current_modeling_phase"] = "planning"
            state["messages"].append(AIMessage(content=f"Vision Analysis:\n{analysis}"))
            
        except Exception as e:
            error_msg = f"Vision analysis failed: {str(e)}"
            self.display_callback(error_msg, "error")
            state["critical_error"] = error_msg
        
        return state
    
    @traceable(name="load_reference_image")
    async def _load_reference_image_node(self, state: SculptorState) -> SculptorState:
        """Load the reference image into Blender scene as a background image"""
        self.display_callback("Loading reference image into Blender...", "info")
        
        try:
            # Use Blender's background image or reference image plane
            # First, let's add an image as an empty/reference plane
            result = await self.mcp.call_tool(
                "execute_python",
                {
                    "code": f"""
import bpy
import os

# Save base64 image to file
image_path = r"{state['input_image_path']}"

# Add reference image as background
if bpy.context.scene.camera:
    cam = bpy.context.scene.camera
    if not cam.data.show_background_images:
        cam.data.show_background_images = True
    
    # Add background image
    bg = cam.data.background_images.new()
    bg.image = bpy.data.images.load(image_path)
    bg.alpha = 0.5

print(f"Reference image loaded: {{image_path}}")
"""
                }
            )
            
            if result["success"]:
                self.display_callback("Reference image loaded successfully", "success")
                state["reference_image_base64"] = state["input_image_base64"]
                state["tool_results"].append({
                    "tool_name": "load_reference_image",
                    "success": True,
                    "result": "Reference image loaded as camera background"
                })
            else:
                self.display_callback(f"Failed to load reference: {result.get('error')}", "error")
                
        except Exception as e:
            self.display_callback(f"Error loading reference: {str(e)}", "error")
        
        return state
    
    @traceable(name="plan_modeling_steps")
    async def _plan_steps_node(self, state: SculptorState) -> SculptorState:
        """Dynamically plan modeling steps based on image analysis and current progress"""
        self.display_callback("Planning modeling steps...", "plan")
        
        # Build context from vision analysis and current state
        context = f"""
VISION ANALYSIS:
{state['vision_analysis']}

CURRENT PHASE: {state['current_modeling_phase']}
STEPS COMPLETED: {state['current_step']}
REPLANNING COUNT: {state.get('replanning_count', 0)}

"""
        
        # Add feedback if available
        if state.get('feedback_history'):
            recent_feedback = state['feedback_history'][-2:]  # Last 2 feedback items
            context += f"\nRECENT FEEDBACK:\n" + "\n".join(recent_feedback)
        
        planning_prompt = f"""{context}

Based on the image analysis above, create a detailed step-by-step plan to model this in Blender.

IMPORTANT GUIDELINES:
1. Start with basic shapes and primitives
2. Build the main structure first, then add details
3. **ALWAYS include steps to create and apply materials with proper colors**
4. Each step should be a single, clear action
5. Use Blender-specific operations (add primitives, modifiers, materials, etc.)
6. Include the Blender compatibility helpers when needed
7. Be specific about positions, scales, rotations, AND COLORS
8. Plan for {8 if state.get('replanning_count', 0) == 0 else 5} steps

**CRITICAL REQUIREMENT**: Your plan MUST include dedicated steps for:
- Creating materials with colors matching the vision analysis
- Applying materials to all visible objects
- Setting material properties (metallic, roughness, etc.)

Do NOT create a plan that results in gray, colorless models.

Generate a JSON array of steps in this format:
[
  {{"step": 1, "action": "Clear default scene and set up workspace", "code_hint": "Delete default objects"}},
  {{"step": 2, "action": "Add base primitive shape", "code_hint": "bpy.ops.mesh.primitive_*_add()"}},
  ...
]

Return ONLY the JSON array, no other text.
"""
        
        messages = [
            SystemMessage(content="You are an expert Blender 3D modeler. Plan efficient modeling workflows."),
            HumanMessage(content=planning_prompt)
        ]
        
        try:
            response = invoke_with_retry_sync(self.reasoning_model, messages)
            plan_text = response.content.strip()
            
            # Extract JSON from response
            if "```json" in plan_text:
                plan_text = plan_text.split("```json")[1].split("```")[0].strip()
            elif "```" in plan_text:
                plan_text = plan_text.split("```")[1].split("```")[0].strip()
            
            steps_data = json.loads(plan_text)
            
            # Extract step descriptions
            steps = [f"Step {s['step']}: {s['action']}" for s in steps_data]
            
            state["planning_steps"] = steps
            state["needs_replanning"] = False
            
            self.display_callback(f"Planned {len(steps)} modeling steps", "success")
            
            # Log steps
            for step in steps:
                self.display_callback(step, "plan")
            
        except Exception as e:
            self.display_callback(f"Planning failed: {str(e)}", "error")
            # Fallback to basic plan
            state["planning_steps"] = [
                "Step 1: Clear scene and set up workspace",
                "Step 2: Add base primitive shapes",
                "Step 3: Position and scale objects",
                "Step 4: Apply modifiers and transformations",
                "Step 5: Add materials and colors",
                "Step 6: Final adjustments"
            ]
        
        return state
    
    @traceable(name="execute_modeling_step")
    async def _execute_step_node(self, state: SculptorState) -> SculptorState:
        """Execute the current modeling step using MCP tool calls"""
        step_idx = state["current_step"]
        
        if step_idx >= len(state["planning_steps"]):
            state["is_complete"] = True
            return state
        
        # Check for cancellation
        if self.cancellation_check():
            state["critical_error"] = "Task cancelled by user"
            return state
        
        current_step = state["planning_steps"][step_idx]
        self.display_callback(f"🔧 Executing: {current_step}", "tool")
        
        # Create execution prompt that lets LLM choose appropriate tools
        execution_prompt = f"""Execute this 3D modeling step in Blender:

{current_step}

Context:
- Vision Analysis: {state['vision_analysis'][:300]}...
- Current Phase: {state['current_modeling_phase']}
- Steps Completed: {step_idx}
- Feedback: {state['feedback_history'][-1] if state['feedback_history'] else 'Starting fresh'}

Use the appropriate Blender MCP tools to accomplish this step.
Available tools include:
- download_polyhaven_asset (for models, textures, HDRIs)
- download_sketchfab_model (for realistic models)
- generate_hyper3d_model_via_text or generate_hyper3d_model_via_images (for custom 3D generation)
- get_scene_info, get_object_info (for inspection)
- execute_blender_code (for materials, colors, and custom operations)
- And other Blender MCP tools

**CRITICAL - MATERIALS & COLORS:**
When creating objects, ALWAYS apply materials with colors matching the vision analysis.
Do NOT leave objects with default gray materials.

Example material creation (SAFE - use this to prevent errors):
```python
import bpy
# After creating an object, apply material using the safe helper
obj = bpy.context.active_object  # or bpy.data.objects.get("ObjectName")
if obj:
    # Use safe helper function (prevents attribute errors)
    mat = create_material_with_color(
        obj,
        mat_name="ColoredMaterial",
        color=(1.0, 0.0, 0.0, 1.0),  # Red (R, G, B, A)
        roughness=0.3,
        metallic=0.0
    )
    if mat:
        print(f"Material applied to {obj.name}")

# For multiple objects
for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.visible_get():
        # Extract color from vision analysis and apply
        create_material_with_color(obj, f"{obj.name}_Material", (0.8, 0.2, 0.2, 1.0))
```

IMPORTANT: Always check integrations first (get_polyhaven_status, get_sketchfab_status, get_hyper3d_status)
before attempting to use them. Use available asset libraries before falling back to manual modeling.
"""
        
        # Get tool schemas for LLM
        tools = self.mcp.get_tools_schema()
        
        # Trim message history to prevent context overflow (keep last 10 messages)
        trimmed_messages = self._trim_message_history(state["messages"], max_messages=10)
        messages = trimmed_messages + [HumanMessage(content=execution_prompt)]
        
        try:
            # Invoke LLM with tools (like artisan agent)
            response = await invoke_with_retry(self.reasoning_model.bind_tools(tools), messages)
            
            # Execute tool calls
            tool_results = []
            tool_messages = []
            
            if hasattr(response, 'tool_calls') and response.tool_calls:
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    self.display_callback(f"🔧 Calling tool: {tool_name}", "tool")
                    self.display_callback(f"   Arguments: {tool_args}", "info")
                    
                    # Call the tool
                    result = await self.mcp.call_tool(tool_name, tool_args)
                    
                    self.display_callback(f"✅ Tool completed: {tool_name}", "success")
                    
                    tool_results.append({
                        "step": step_idx + 1,
                        "tool_name": tool_name,
                        "arguments": tool_args,
                        "result": result
                    })
                    
                    # Create tool message for conversation
                    tool_messages.append(ToolMessage(
                        content=json.dumps(result),
                        tool_call_id=tool_call["id"]
                    ))
            else:
                self.display_callback("⚠️ No tool calls generated, LLM responded with text", "info")
                tool_results.append({
                    "step": step_idx + 1,
                    "tool_name": "none",
                    "result": response.content
                })
            
            state["tool_results"].extend(tool_results)
            state["messages"].append(response)
            state["messages"].extend(tool_messages)
            state["current_step"] += 1
            
            self.display_callback(f"✅ ✓ Step {step_idx + 1} executed successfully", "success")
            
            # Add delay to prevent rate limits
            await asyncio.sleep(RATE_LIMIT_STEP_DELAY)
            
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            self.display_callback(error_msg, "error")
            state["tool_results"].append({
                "step": step_idx + 1,
                "tool_name": "error",
                "success": False,
                "result": error_msg
            })
            state["current_step"] += 1
        
        return state
    
    @traceable(name="capture_viewport_feedback")
    async def _capture_feedback_node(self, state: SculptorState) -> SculptorState:
        """Capture screenshot and compare with input image"""
        # Small delay to ensure Blender viewport has updated
        await asyncio.sleep(1.0)
        
        self.display_callback("Capturing viewport screenshot...", "screenshot")
        
        try:
            # Use get_viewport_screenshot like artisan agent (returns base64 directly, no file sync needed)
            result = await self.mcp.call_tool(
                "get_viewport_screenshot",
                {"max_size": 800}
            )
            
            if result["success"] and result.get("image_data"):
                screenshot_base64 = result["image_data"]
                
                # Save screenshot to file for reference
                screenshot_path = state["screenshot_dir"] / f"step_{state['current_step']:03d}.png"
                image_bytes = base64.b64decode(screenshot_base64)
                screenshot_path.write_bytes(image_bytes)
                
                state["screenshot_count"] += 1
                self.display_callback(f"Screenshot saved: {screenshot_path.name}", "success")
                
                # Compare with input image using vision model
                comparison_prompt = f"""Compare these two images:

LEFT: Original input image (the target 2D image to recreate)
RIGHT: Current 3D model viewport (Blender screenshot)

Analyze:
1. **Overall Match**: How well does the 3D model match the input? (0-100%)
2. **Shape Accuracy**: Are the main shapes/forms correct?
3. **Colors & Materials**: Do the colors match the input image?
   - **CRITICAL**: Are objects gray/colorless (this is BAD - means no materials applied)?
   - Do the colors match what's in the original image?
   - Are materials realistic (metallic, rough, glossy, etc.)?
4. **Position & Layout**: Are objects positioned correctly?
5. **Missing Elements**: What's missing from the 3D model?
6. **Incorrect Elements**: What needs to be fixed?
7. **Next Steps**: What should be improved next?

**CRITICAL CHECK**: If the 3D model has default gray materials while the input image has colors, this is a MAJOR issue.

Current phase: {state['current_modeling_phase']}
Steps completed: {state['current_step']} / {len(state['planning_steps'])}

Provide constructive feedback to guide the modeling process, with special attention to color/material matching.
"""
                
                messages = [
                    HumanMessage(
                        content=[
                            {"type": "text", "text": comparison_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{state['input_image_media_type']};base64,{state['input_image_base64']}"
                                }
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{screenshot_base64}"
                                }
                            }
                        ]
                    )
                ]
                
                feedback_response = await invoke_with_retry(self.vision_model, messages)
                feedback = feedback_response.content
                
                state["feedback_history"].append(f"Step {state['current_step']}: {feedback[:300]}...")
                
                # Extract quality score if mentioned
                quality_score = 50  # Default
                if "%" in feedback:
                    try:
                        # Try to extract percentage
                        import re
                        matches = re.findall(r'(\d+)%', feedback)
                        if matches:
                            quality_score = int(matches[0])
                    except:
                        pass
                
                state["quality_scores"].append({
                    "step": state["current_step"],
                    "score": quality_score,
                    "feedback": feedback
                })
                
                self.display_callback(f"Quality score: {quality_score}%", "info")
                
            else:
                self.display_callback(f"Screenshot failed: {result.get('error')}", "error")
                
        except Exception as e:
            self.display_callback(f"Feedback capture error: {str(e)}", "error")
        
        return state
    
    @traceable(name="assess_modeling_progress")
    async def _assess_progress_node(self, state: SculptorState) -> SculptorState:
        """Assess progress and decide if replanning is needed"""
        
        # Check if all steps are complete
        if state["current_step"] >= len(state["planning_steps"]):
            # Check quality scores
            if state["quality_scores"]:
                avg_score = sum(q["score"] for q in state["quality_scores"][-3:]) / min(3, len(state["quality_scores"]))
                
                if avg_score >= 75:
                    state["is_complete"] = True
                    state["current_modeling_phase"] = "complete"
                    self.display_callback(f"Modeling complete! Average quality: {avg_score:.1f}%", "success")
                elif state["replanning_count"] < state["max_replanning_attempts"]:
                    state["needs_replanning"] = True
                    state["replanning_count"] += 1
                    state["current_modeling_phase"] = "refinement"
                    self.display_callback(f"Quality below threshold ({avg_score:.1f}%), replanning...", "info")
                else:
                    state["is_complete"] = True
                    self.display_callback(f"Max replanning attempts reached. Final quality: {avg_score:.1f}%", "info")
            else:
                state["is_complete"] = True
        
        return state
    
    def _should_continue(self, state: SculptorState) -> str:
        """Decide whether to replan, continue, or complete"""
        if state.get("critical_error"):
            return "complete"
        
        if state.get("is_complete"):
            return "complete"
        
        if state.get("needs_replanning"):
            return "replan"
        
        return "continue"
    
    @traceable(name="complete_modeling")
    def _complete_node(self, state: SculptorState) -> SculptorState:
        """Complete the modeling process"""
        if state.get("critical_error"):
            self.display_callback(f"Modeling halted: {state['critical_error']}", "error")
        else:
            self.display_callback("Modeling process complete!", "success")
            
            if state["quality_scores"]:
                final_score = state["quality_scores"][-1]["score"]
                self.display_callback(f"Final quality score: {final_score}%", "info")
        
        state["is_complete"] = True
        return state
    
    @staticmethod
    def generate_session_id(image_path: str) -> str:
        """Generate deterministic session ID from image path"""
        from hashlib import md5
        return md5(image_path.encode()).hexdigest()[:16]
    
    def _backend_to_blender_path(self, backend_path: Path) -> str:
        """Convert backend screenshot path to Blender container path"""
        # Backend: screenshots/sculptor/session_id/file.png
        # Blender: /blender_projects/screenshots/sculptor/session_id/file.png
        return str(Path("/blender_projects") / backend_path)
    
    async def _wait_for_file_and_read(self, file_path: Path, timeout: float = 15.0, check_interval: float = 0.1) -> str:
        """
        Asynchronously wait for a file to appear and read it
        
        Args:
            file_path: Path to file
            timeout: Maximum time to wait in seconds
            check_interval: How often to check for file existence in seconds
            
        Returns:
            Base64 encoded file content
            
        Raises:
            TimeoutError: If file doesn't appear within timeout
            IOError: If file can't be read
        """
        start_time = asyncio.get_event_loop().time()
        elapsed = 0
        
        self.display_callback(f"Waiting for file sync (timeout: {timeout}s)...", "info")
        
        while elapsed < timeout:
            try:
                # Check if file exists and is readable
                if file_path.exists() and file_path.stat().st_size > 0:
                    # File exists and has content, try to read it
                    try:
                        with open(file_path, "rb") as f:
                            content = f.read()
                        
                        # Verify we got content
                        if len(content) > 0:
                            self.display_callback(f"Screenshot loaded after {elapsed:.2f}s", "success")
                            return base64.b64encode(content).decode()
                        else:
                            # Empty file, wait for content
                            self.display_callback(f"File empty, waiting... ({elapsed:.1f}s)", "info")
                    except (IOError, OSError) as e:
                        # File is being written, wait
                        self.display_callback(f"File locked, waiting... ({elapsed:.1f}s)", "info")
                
                # Wait before next check
                await asyncio.sleep(check_interval)
                elapsed = asyncio.get_event_loop().time() - start_time
                
            except Exception as e:
                # Log but continue waiting
                self.display_callback(f"Check error: {str(e)}, continuing...", "info")
                await asyncio.sleep(check_interval)
                elapsed = asyncio.get_event_loop().time() - start_time
        
        # Timeout reached
        raise TimeoutError(f"Screenshot file did not sync within {timeout}s: {file_path}")
    
    @traceable(name="run_sculptor_task")
    async def run(self, image_path: str, use_deterministic_session: bool = True) -> Dict[str, Any]:
        """
        Run the sculptor agent on an input image
        
        Args:
            image_path: Path to input 2D image
            use_deterministic_session: Use deterministic session ID for resume
            
        Returns:
            Dict with results
        """
        # Load and encode image
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Input image not found: {image_path}")
        
        with open(image_path_obj, "rb") as f:
            image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode()
        
        # Detect image format from file extension
        image_ext = image_path_obj.suffix.lower()
        if image_ext in ['.jpg', '.jpeg']:
            image_media_type = 'image/jpeg'
        elif image_ext == '.png':
            image_media_type = 'image/png'
        elif image_ext == '.webp':
            image_media_type = 'image/webp'
        elif image_ext == '.gif':
            image_media_type = 'image/gif'
        else:
            image_media_type = 'image/png'  # Default to PNG
        
        # Create screenshot directory using shared volume path
        screenshot_dir = Path("screenshots/sculptor") / self.session_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine session ID
        if use_deterministic_session:
            session_key = self.generate_session_id(image_path)
        else:
            session_key = self.session_id
        
        # Initialize state
        initial_state: SculptorState = {
            "messages": [],
            "session_id": self.session_id,
            "screenshot_dir": screenshot_dir,
            "input_image_path": str(image_path_obj.absolute()),
            "input_image_base64": image_base64,
            "input_image_media_type": image_media_type,
            "reference_image_base64": None,
            "tool_results": [],
            "screenshot_count": 0,
            "planning_steps": [],
            "current_step": 0,
            "is_complete": False,
            "feedback_history": [],
            "vision_analysis": "",
            "current_modeling_phase": "planning",
            "needs_replanning": False,
            "quality_scores": [],
            "critical_error": None,
            "max_replanning_attempts": 2,
            "replanning_count": 0
        }
        
        self.display_callback("="*60, "info")
        self.display_callback(f"Starting Sculptor Agent", "info")
        self.display_callback(f"Input Image: {image_path}", "info")
        self.display_callback(f"Session: {self.session_id}", "info")
        self.display_callback("="*60, "info")
        
        try:
            # Set high recursion limit for multi-step workflows
            # Each step goes through: analyze → load → plan → execute → capture → assess → (loop)
            # For complex models with replanning loops, we need higher limits
            recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "100"))
            
            config = {
                "configurable": {"thread_id": session_key},
                "recursion_limit": recursion_limit
            }
            
            self.display_callback(f"Starting workflow with recursion limit: {recursion_limit}...", "info")
            
            final_state = None
            async for state_update in self.graph.astream(initial_state, config):
                if self.cancellation_check():
                    self.display_callback("Task cancelled by user", "error")
                    return {
                        "success": False,
                        "session_id": self.session_id,
                        "steps_executed": initial_state["current_step"],
                        "screenshots_captured": initial_state["screenshot_count"],
                        "screenshot_directory": str(screenshot_dir),
                        "tool_results": initial_state["tool_results"],
                        "error": "Cancelled by user"
                    }
                
                # Get the latest state
                for node_name, node_state in state_update.items():
                    final_state = node_state
            
            if final_state is None:
                final_state = initial_state
            
            success = final_state.get("is_complete", False) and not final_state.get("critical_error")
            
            return {
                "success": success,
                "session_id": self.session_id,
                "steps_executed": final_state["current_step"],
                "screenshots_captured": final_state["screenshot_count"],
                "screenshot_directory": str(screenshot_dir),
                "tool_results": final_state["tool_results"],
                "quality_scores": final_state.get("quality_scores", []),
                "vision_analysis": final_state.get("vision_analysis", ""),
                "error": final_state.get("critical_error")
            }
            
        except GraphRecursionError as e:
            self.display_callback("Recursion limit reached", "error")
            return {
                "success": False,
                "session_id": self.session_id,
                "steps_executed": initial_state["current_step"],
                "screenshots_captured": initial_state["screenshot_count"],
                "screenshot_directory": str(screenshot_dir),
                "tool_results": initial_state["tool_results"],
                "error": "Recursion limit reached",
                "recursion_limit_reached": True
            }
        except Exception as e:
            self.display_callback(f"Error: {str(e)}", "error")
            traceback.print_exc()
            return {
                "success": False,
                "session_id": self.session_id,
                "steps_executed": initial_state.get("current_step", 0),
                "screenshots_captured": initial_state.get("screenshot_count", 0),
                "screenshot_directory": str(screenshot_dir),
                "tool_results": initial_state.get("tool_results", []),
                "error": str(e)
            }
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            # Only cleanup MCP if we own it
            if self.owns_mcp:
                await self.mcp.cleanup()
        except Exception:
            pass
