"""
Artisan Agent - Autonomous 3D Modeling Agent for Blender
Uses LangGraph for reasoning and sequential tool execution
"""
import os
import asyncio
import base64
import json
import logging
import hashlib
import time
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
from langgraph.prebuilt import ToolNode
from langgraph.errors import GraphRecursionError

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Configure LangSmith
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "true"

# Rate limit handling
async def invoke_with_retry(model, messages, max_retries=3):
    """Invoke LLM with exponential backoff for rate limits"""
    for attempt in range(max_retries):
        try:
            return await model.ainvoke(messages)
        except Exception as e:
            if "rate_limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = (2 ** attempt) * 5  # 5s, 10s, 20s
                logging.warning(f"Rate limit hit, waiting {wait_time}s before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(wait_time)
            else:
                raise

# Blender Version Compatibility Helper
BLENDER_COMPAT_CODE = '''
# Blender 4.x/5.x compatibility helper
import bpy

def set_principled_bsdf_property(bsdf, property_name, value):
    """Set BSDF property with version compatibility"""
    # Blender 4.x renamed some properties
    property_mapping = {
        'Specular': 'Specular IOR',  # Blender 4.x change
        'Emission': 'Emission Color',  # Blender 4.x change
    }
    
    # Try original name first
    try:
        bsdf.inputs[property_name].default_value = value
        return True
    except KeyError:
        # Try mapped name if original fails
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
    # Blender 4.0+ removed Musgrave, replaced with enhanced Noise Texture
    if node_type == 'ShaderNodeTexMusgrave':
        # Use Noise Texture instead (available in all versions)
        node = node_tree.nodes.new(type='ShaderNodeTexNoise')
        node.name = name
        node.location = location
        # Set noise type to approximate Musgrave behavior
        if hasattr(node, 'noise_type'):
            node.noise_type = 'FBM'  # Fractal Brownian Motion approximates Musgrave
        return node
    else:
        # Standard node creation
        node = node_tree.nodes.new(type=node_type)
        node.name = name
        node.location = location
        return node
'''


class AgentState(TypedDict):
    """State of the Artisan Agent"""
    messages: Annotated[Sequence[BaseMessage], "Conversation messages"]
    requirement: str  # The refined prompt from JSON
    session_id: str  # Unique session identifier
    screenshot_dir: Path  # Directory for storing screenshots
    tool_results: List[Dict[str, Any]]  # Results from tool executions
    screenshot_count: int  # Number of screenshots taken
    planning_steps: List[str]  # Planned steps for execution
    current_step: int  # Current step being executed
    is_complete: bool  # Whether modeling is complete
    feedback_history: List[str]  # Visual feedback from screenshots
    initial_scene_state: Dict[str, Any]  # Initial Blender scene state
    completed_steps: List[str]  # Steps already completed (for resume)
    is_resuming: bool  # Whether this is a resumed session
    critical_error: Optional[str]  # Critical error that halts execution
    # Refinement loop fields
    vision_feedback: List[str]  # Vision-based quality feedback from screenshots
    execution_errors: List[str]  # Execution errors for debugging
    quality_scores: List[Dict[str, Any]]  # Quality scores per step
    refinement_attempts: int  # Number of refinement attempts for current step
    max_refinements_per_step: int  # Maximum refinements allowed per step
    needs_refinement: bool  # Whether current step needs refinement
    refinement_feedback: Optional[str]  # Specific feedback for refinement
    enable_refinement: bool  # Whether refinement loop is enabled (from JSON config)


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
        # Pass environment variables to subprocess
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
        await self.mcp_session.initialize()
        
        # Get available tools
        tools_response = await self.mcp_session.list_tools()
        self.tools = {t.name: t for t in tools_response.tools}
        
        return len(self.tools)
    
    @traceable(name="call_blender_tool")
    async def call_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Call a Blender MCP tool"""
        try:
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            # Extract text and images from result
            result_text = ""
            image_data = None
            
            for content in result.content:
                if hasattr(content, 'text'):
                    result_text += content.text
                elif hasattr(content, 'data') and hasattr(content, 'mimeType'):
                    if content.mimeType.startswith('image/'):
                        if isinstance(content.data, bytes):
                            image_data = base64.b64encode(content.data).decode('utf-8')
                        else:
                            image_data = content.data
                        result_text += f'\n[Image captured: {len(image_data)} bytes]'
            
            return {
                "success": True,
                "result": result_text,
                "tool_name": tool_name,
                "arguments": arguments,
                "image_data": image_data
            }
        except Exception as e:
            return {
                "success": False,
                "result": f"Error: {str(e)}",
                "tool_name": tool_name,
                "arguments": arguments
            }
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self._cleanup_done:
            return
        
        try:
            # Close session first
            if self.session_context:
                try:
                    await self.session_context.__aexit__(None, None, None)
                except (RuntimeError, GeneratorExit, BaseExceptionGroup, Exception):
                    # Suppress all cleanup errors - connection is already closed
                    pass
            
            # Then close stdio context
            if self.stdio_context:
                try:
                    await self.stdio_context.__aexit__(None, None, None)
                except (RuntimeError, GeneratorExit, BaseExceptionGroup, Exception):
                    # Suppress stdio cleanup errors
                    pass
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
                "description": tool.description or f"Execute {tool_name}",
                "input_schema": tool.inputSchema or {"type": "object", "properties": {}}
            })
        return tools_schema


class ArtisanAgent:
    """
    Autonomous 3D modeling agent that:
    1. Reads modeling requirements from JSON
    2. Plans sequential steps
    3. Executes Blender MCP tools
    4. Captures screenshots for feedback
    5. Iterates until completion
    """
    
    def __init__(self, session_id: Optional[str] = None, display_callback: Optional[callable] = None, cancellation_check: Optional[callable] = None):
        """
        Initialize the Artisan Agent
        
        Args:
            session_id: Optional session ID (generated if not provided)
            display_callback: Optional callback for displaying progress (for Streamlit)
            cancellation_check: Optional callback that returns True if task should be cancelled
        """
        self.session_id = session_id or str(uuid4())
        self.display_callback = display_callback or self._console_display
        self.cancellation_check = cancellation_check or (lambda: False)
        
        # Initialize LLM
        self.llm = ChatAnthropic(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Initialize Blender MCP
        self.mcp = BlenderMCPConnection()
        
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
            "thinking": "🤔"
        }
        print(f"{icons.get(type, '•')} {message}")
    
    @traceable(name="initialize_artisan_agent")
    async def initialize(self):
        """Initialize agent and MCP connection"""
        self.display_callback("Initializing Artisan Agent...", "info")
        
        # Connect to Blender
        num_tools = await self.mcp.initialize()
        self.display_callback(f"Connected to Blender with {num_tools} tools", "success")
        
        # Build the graph
        self.graph = self._create_graph()
        self.display_callback("Agent workflow initialized", "success")
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow with refinement loop"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_scene", self._analyze_scene_node)
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("capture_feedback", self._capture_feedback_node)
        workflow.add_node("assess_quality", self._assess_quality_node)  # NEW: Quality assessment
        workflow.add_node("refine_step", self._refine_step_node)  # NEW: Refinement execution
        workflow.add_node("evaluate_progress", self._evaluate_progress_node)
        workflow.add_node("complete", self._complete_node)
        
        # Set entry point - start with scene analysis
        workflow.set_entry_point("analyze_scene")
        
        # Add edges
        workflow.add_edge("analyze_scene", "plan")
        workflow.add_edge("plan", "execute_step")
        workflow.add_edge("execute_step", "capture_feedback")
        workflow.add_edge("capture_feedback", "assess_quality")  # NEW: Always assess quality
        
        # NEW: Conditional edge from quality assessment
        workflow.add_conditional_edges(
            "assess_quality",
            self._should_refine,
            {
                "refine": "refine_step",  # Quality issues detected - refine
                "continue": "evaluate_progress"  # Quality acceptable - continue
            }
        )
        
        # NEW: After refinement, capture feedback again
        workflow.add_edge("refine_step", "capture_feedback")
        
        # Conditional edge: continue or complete
        workflow.add_conditional_edges(
            "evaluate_progress",
            self._should_continue,
            {
                "continue": "execute_step",
                "complete": "complete"
            }
        )
        
        workflow.add_edge("complete", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    @traceable(name="analyze_scene_state")
    async def _analyze_scene_node(self, state: AgentState) -> AgentState:
        """Analyze current Blender scene to detect existing work"""
        logger = logging.getLogger(__name__)
        self.display_callback("Analyzing current scene state...", "info")
        
        # Get scene info
        scene_info_result = await self.mcp.call_tool("get_scene_info", {})
        
        # Capture initial viewport screenshot
        screenshot_result = await self.mcp.call_tool("get_viewport_screenshot", {"max_size": 800})
        
        initial_state = {
            "scene_info": scene_info_result.get("result", "No scene info"),
            "has_screenshot": screenshot_result["success"],
            "objects_present": "objects" in scene_info_result.get("result", "").lower()
        }
        
        # Save initial screenshot if available
        if screenshot_result["success"] and screenshot_result.get("image_data"):
            screenshot_path = state["screenshot_dir"] / "initial_scene.png"
            image_bytes = base64.b64decode(screenshot_result["image_data"])
            screenshot_path.write_bytes(image_bytes)
            logger.info(f"Saved initial scene screenshot: {screenshot_path}")
            self.display_callback("Initial scene captured", "screenshot")
        
        state["initial_scene_state"] = initial_state
        
        # Log scene state
        logger.info(f"Initial scene state: {json.dumps(initial_state, indent=2)}")
        self.display_callback(f"Scene objects detected: {initial_state['objects_present']}", "info")
        
        return state
    
    @traceable(name="plan_modeling_steps")
    async def _plan_node(self, state: AgentState) -> AgentState:
        """Plan the steps needed to complete the 3D modeling task"""
        logger = logging.getLogger(__name__)
        self.display_callback("Planning modeling steps...", "plan")
        
        # Check if scene has existing work
        scene_state = state.get("initial_scene_state", {})
        scene_info = scene_state.get("scene_info", "Empty scene")
        has_existing_work = scene_state.get("objects_present", False)
        
        # Build planning prompt with scene context
        scene_context = ""
        if has_existing_work:
            scene_context = f"""

CURRENT SCENE STATE:
{scene_info}

IMPORTANT: The scene already contains objects. Analyze what's been done and continue building from there.
Do NOT start from scratch - build upon existing work."""
            
            self.display_callback("Detected existing work - planning to resume", "thinking")
            state["is_resuming"] = True
        else:
            self.display_callback("Starting fresh - no existing work detected", "info")
            state["is_resuming"] = False
        
        planning_prompt = f"""You are an expert 3D modeling planner for Blender. 
        
Given this modeling requirement, break it down into sequential, actionable steps.
Each step should be a specific Blender operation that can be executed.

Requirement:
{state['requirement']}...{scene_context}

Create a detailed step-by-step plan. Each step should:
1. Be specific and actionable
2. Use available Blender MCP tools
3. Build upon previous steps
4. Include intermediate checks with viewport screenshots

Available tools: execute_blender_code, get_scene_info, get_viewport_screenshot, get_object_info

IMPORTANT: Format your response as a clear numbered list:
1. First step description
2. Second step description
3. Third step description
...

Provide at least 5-10 concrete steps to build the model."""

        messages = [HumanMessage(content=planning_prompt)]
        logger.info("Sending planning request to LLM...")
        response = self.llm.invoke(messages)

        print(f"📝"*60)
        # print(f"📝 Requirement preview: {state['requirement'][:1000]}")
        print(planning_prompt)
        print(f"---"*60)

        # Parse steps from response
        steps_text = response.content
        logger.info(f"LLM response length: {len(steps_text)} characters")
        logger.debug(f"LLM response:\n{steps_text[:500]}...")
        
        # Better step parsing - look for numbered lines
        lines = steps_text.split('\n')
        steps = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Match patterns like "1.", "1)", "Step 1:", etc.
            if any([
                line[:3].strip().endswith('.') and line[0].isdigit(),
                line[:3].strip().endswith(')') and line[0].isdigit(),
                line.lower().startswith('step ') and any(c.isdigit() for c in line[:10])
            ]):
                # Remove the numbering prefix
                step_text = line
                for prefix in ['Step ', 'step ', '.', ')', ':']:
                    if prefix in step_text[:20]:
                        parts = step_text.split(prefix, 1)
                        if len(parts) > 1:
                            step_text = parts[1].strip()
                            break
                steps.append(step_text)
        
        logger.info(f"Parsed {len(steps)} steps from LLM response")
        if len(steps) == 0:
            logger.warning("No steps parsed from LLM response! Using fallback plan.")
            # Fallback: Create a basic plan
            steps = [
                "Clear default scene and set up environment",
                "Create main geometry based on requirements",
                "Add details and refinements",
                "Apply materials and lighting",
                "Final adjustments and capture screenshot"
            ]
            logger.info(f"Using fallback plan with {len(steps)} steps")
        
        for i, step in enumerate(steps, 1):
            logger.debug(f"Step {i}: {step[:100]}")
        
        # If resuming, detect completed steps with detailed object inspection
        # CRITICAL: Only attempt resume if there are SUBSTANTIAL objects (not just templates)
        if state.get("is_resuming", False) and scene_state.get("objects_present", False):
            # SAFETY: Check if we actually have meaningful geometry
            import json
            try:
                scene_data = json.loads(scene_info)
                num_objects = len(scene_data.get("objects", []))
                
                # If we only have 1-3 objects, likely just templates - start fresh
                if num_objects <= 3:
                    logger.warning(f"Only {num_objects} objects found - likely templates, starting fresh")
                    self.display_callback("Few objects detected - building from scratch", "info")
                    state["completed_steps"] = []
                    state["current_step"] = 0
                    state["planning_steps"] = steps
                    return state
            except:
                pass
                
            logger.info("Analyzing which steps are already completed...")
            self.display_callback("Detecting completed work...", "thinking")
            
            # Get detailed object information for better detection
            object_details = []
            try:
                import json
                scene_data = json.loads(scene_info)
                for obj in scene_data.get("objects", [])[:5]:  # Inspect first 5 objects in detail
                    obj_info_result = await self.mcp.call_tool("get_object_info", {"object_name": obj["name"]})
                    if obj_info_result["success"]:
                        object_details.append(f"{obj['name']}: {obj_info_result['result'][:200]}")
            except Exception as e:
                logger.warning(f"Could not get detailed object info: {e}")
            
            detailed_scene_context = f"""
Scene Summary: {scene_info}

Detailed Object Inspection (first 5 objects):
{chr(10).join(object_details) if object_details else 'Could not inspect objects in detail'}
"""
            
            # Ask LLM to identify completed steps with strict criteria
            detection_prompt = f"""Based on the current scene state, identify which of these planned steps appear to be FULLY completed with actual geometry, not just placeholder objects.

Planned Steps:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(steps))}

Current Scene:
{detailed_scene_context}

IMPORTANT CRITERIA:
- Only mark a step as done if there is SUBSTANTIAL geometry present (not empty curves, not basic primitives)
- Look for evidence of modifiers, particle systems, complex geometry, materials applied
- Empty or placeholder objects (like named curves with no geometry) do NOT count as completed
- Be VERY conservative - when in doubt, mark as NOT done

Respond with ONLY the step numbers that are FULLY completed (e.g., "1,2,3" or "none" if starting fresh).
If objects exist but appear to be placeholders or incomplete, respond with "none"."""
            
            detection_response = self.llm.invoke([HumanMessage(content=detection_prompt)])
            completed_text = detection_response.content.strip().lower()
            
            logger.info(f"LLM completed steps detection: {completed_text}")
            
            # Parse completed step numbers
            completed_indices = []
            if completed_text != "none" and completed_text:
                try:
                    # Extract numbers from response
                    import re
                    numbers = re.findall(r'\d+', completed_text)
                    completed_indices = [int(n) - 1 for n in numbers if 0 <= int(n) - 1 < len(steps)]
                    
                    # Additional safety: Don't skip more than 30% of steps to avoid false positives
                    max_skip = max(1, int(len(steps) * 0.3))
                    if len(completed_indices) > max_skip:
                        logger.warning(f"LLM detected {len(completed_indices)} completed steps, but limiting to {max_skip} for safety")
                        completed_indices = completed_indices[:max_skip]
                except Exception as e:
                    logger.warning(f"Could not parse completed steps: {e}")
            
            if completed_indices:
                state["completed_steps"] = [steps[i] for i in completed_indices]
                state["current_step"] = max(completed_indices) + 1
                logger.info(f"Resuming from step {state['current_step'] + 1} (skipped {len(completed_indices)} completed steps)")
                self.display_callback(f"Resuming from step {state['current_step'] + 1} (found {len(completed_indices)} completed)", "success")
            else:
                state["completed_steps"] = []
                state["current_step"] = 0
                logger.info("No completed steps detected, starting from beginning")
                self.display_callback("No completed steps detected - building from scratch", "info")
        else:
            state["completed_steps"] = []
            state["current_step"] = 0
        
        state["planning_steps"] = steps
        state["messages"].append(AIMessage(content=f"Created plan with {len(steps)} steps (starting at step {state['current_step'] + 1})"))
        
        self.display_callback(f"Created {len(steps)}-step plan", "success")
        
        # Show completed steps if resuming
        if state.get("completed_steps"):
            self.display_callback(f"✓ Skipping {len(state['completed_steps'])} completed steps", "success")
            for i, step in enumerate(state["completed_steps"], 1):
                self.display_callback(f"  ✓ {i}. {step[:80]}", "success")
        
        # Show remaining steps to execute
        remaining_steps = steps[state["current_step"]:]
        for i, step in enumerate(remaining_steps[:5], state["current_step"] + 1):
            self.display_callback(f"  {i}. {step[:100]}", "plan")
        if len(remaining_steps) > 5:
            self.display_callback(f"  ... and {len(remaining_steps) - 5} more steps", "plan")
        
        return state
    
    @traceable(name="execute_modeling_step")
    async def _execute_step_node(self, state: AgentState) -> AgentState:
        """Execute the current modeling step"""
        logger = logging.getLogger(__name__)
        
        # Check for cancellation
        if self.cancellation_check():
            logger.info("Task cancelled - stopping execution")
            state["is_complete"] = True
            state["critical_error"] = "Task cancelled by user"
            return state
        
        current_idx = state["current_step"]
        
        logger.info(f"Execute step node - current_step: {current_idx}, total_steps: {len(state['planning_steps'])}")
        
        if current_idx >= len(state["planning_steps"]):
            logger.info("All steps completed, setting is_complete=True")
            state["is_complete"] = True
            return state
        
        current_step = state["planning_steps"][current_idx]
        logger.info(f"Executing step {current_idx + 1}/{len(state['planning_steps'])}: {current_step[:100]}")
        self.display_callback(f"Step {current_idx + 1}/{len(state['planning_steps'])}: {current_step[:100]}", "tool")
        
        # Create a prompt for Claude to execute this step
        execution_prompt = f"""Execute this modeling step in Blender:

{current_step}

Previous context:
{chr(10).join(state['feedback_history'][-2:]) if state['feedback_history'] else 'Starting fresh'}

IMPORTANT - Blender Version Compatibility:
This project must work with Blender 4.x and 5.x. Use these compatibility helpers:

{BLENDER_COMPAT_CODE}

**CRITICAL Node Compatibility:**
- **Musgrave Texture (REMOVED in Blender 4.0+)**: Use `create_texture_node(nodes, 'ShaderNodeTexMusgrave', ...)` instead
- **Noise Texture**: Use `nodes.new(type='ShaderNodeTexNoise')` directly (works in all versions)
- The helper automatically converts Musgrave to Noise Texture with FBM type

Example usage:
```python
# For BSDF properties
bsdf = mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (1.0, 0.0, 0.0, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.5
    # Use helper for renamed properties
    set_principled_bsdf_property(bsdf, 'Specular', 0.5)  # Handles Blender 4.x rename
    set_principled_bsdf_property(bsdf, 'Emission', (1.0, 1.0, 1.0, 1.0))  # Handles Blender 4.x rename

# For texture nodes (handles Musgrave → Noise conversion)
musgrave = create_texture_node(mat.node_tree, 'ShaderNodeTexMusgrave', 'Fine_Grain', (-1200, -200))
musgrave.inputs['Scale'].default_value = 50.0
# Note: In Blender 4.x, this becomes a Noise Texture with FBM type automatically
```

Use the appropriate Blender MCP tools to accomplish this step.
For code execution, use execute_blender_code.
After significant changes, get a viewport screenshot for verification."""

        # Get tool schemas for Claude
        tools = self.mcp.get_tools_schema()
        logger.info(f"Available tools: {len(tools)}")
        
        messages = list(state["messages"]) + [HumanMessage(content=execution_prompt)]
        
        # Invoke Claude with tools
        logger.info("Invoking LLM to determine tool calls...")
        response = self.llm.bind_tools(tools).invoke(messages)
        
        # Execute tool calls
        tool_results = []
        tool_messages = []
        if hasattr(response, 'tool_calls') and response.tool_calls:
            logger.info(f"LLM requested {len(response.tool_calls)} tool calls")
            for tool_call in response.tool_calls:
                logger.info(f"Calling tool: {tool_call['name']} with args: {str(tool_call.get('args', {}))[:200]}")
                self.display_callback(f"  🔧 Calling: {tool_call['name']}", "tool")
                
                result = await self.mcp.call_tool(
                    tool_call['name'],
                    tool_call.get('args', {})
                )
                
                logger.info(f"Tool {tool_call['name']} result: success={result['success']}")
                tool_results.append(result)
                
                # Create ToolMessage for conversation history
                tool_message = ToolMessage(
                    content=str(result['result']) if result['success'] else f"Error: {result['result']}",
                    tool_call_id=tool_call['id']
                )
                tool_messages.append(tool_message)
                
                # ENHANCED: Check for errors even when success=True
                result_str = str(result.get('result', '')).lower()
                has_error = (
                    not result.get('success', False) or
                    'error' in result_str or
                    'failed' in result_str or
                    'not found' in result_str
                )
                
                if has_error:
                    error_msg = result.get('result', '')[:200]
                    logger.error(f"Tool {tool_call['name']} had errors: {error_msg}")
                    self.display_callback(f"  ⚠️ {tool_call['name']} completed with errors", "error")
                    self.display_callback(f"Tool {tool_call['name']} had errors: {error_msg}", "error")
                    
                    # Store error for later analysis
                    if "execution_errors" not in state:
                        state["execution_errors"] = []
                    state["execution_errors"].append(f"Step {state['current_step']}: {error_msg}")
                    
                    # CRITICAL: Halt on Blender code execution errors in early steps
                    if tool_call['name'] == 'execute_blender_code' and state['current_step'] <= 5:
                        error_lower = str(result.get('result', '')).lower()
                        if any(pattern in error_lower for pattern in ['not found', 'no attribute', 'keyerror']):
                            state['critical_error'] = f"Step {state['current_step']} failed: {error_msg}"
                            logger.critical(f"🛑 CRITICAL ERROR in step {state['current_step']}: {error_msg}")
                            self.display_callback(f"🛑 CRITICAL ERROR: {error_msg}", "error")
                            self.display_callback("Execution halted due to critical error", "error")
                            return state
                else:
                    self.display_callback(f"  ✅ {tool_call['name']} completed", "success")
        else:
            logger.warning("LLM did not request any tool calls!")
            if hasattr(response, 'content'):
                logger.info(f"LLM response: {response.content[:200]}")
        
        state["tool_results"].extend(tool_results)
        # Add both the AI response and the tool messages to maintain proper conversation flow
        state["messages"].append(response)
        state["messages"].extend(tool_messages)
        state["current_step"] += 1
        
        return state
    
    @traceable(name="capture_viewport_feedback")
    async def _capture_feedback_node(self, state: AgentState) -> AgentState:
        """Capture viewport screenshot and analyze with vision model"""
        logger = logging.getLogger(__name__)
        self.display_callback("📸 Capturing viewport screenshot...", "screenshot")
        
        # Adjust camera to see all objects (prevent occlusion)
        camera_code = '''
import bpy

# Frame all objects in viewport to prevent occlusion
try:
    # Switch to a better view angle (3D view with good perspective)
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            for space in area.spaces:
                if space.type == 'VIEW_3D':
                    # Set to front-right-top perspective for better visibility
                    space.region_3d.view_rotation = (0.8205, 0.4247, 0.1920, 0.3272)
                    # Frame all visible objects
                    override = bpy.context.copy()
                    override['area'] = area
                    override['region'] = area.regions[-1]
                    with bpy.context.temp_override(**override):
                        bpy.ops.view3d.view_all(center=False)
                    break
            break
except Exception as e:
    print(f"Camera adjustment failed: {e}")
'''
        await self.mcp.call_tool("execute_blender_code", {"code": camera_code})
        
        # Call screenshot tool
        screenshot_result = await self.mcp.call_tool("get_viewport_screenshot", {"max_size": 800})
        
        if screenshot_result["success"] and screenshot_result.get("image_data"):
            # Save screenshot
            screenshot_count = state["screenshot_count"]
            refine_suffix = f"_refine{state.get('refinement_attempts', 0)}" if state.get('refinement_attempts', 0) > 0 else ""
            screenshot_path = state["screenshot_dir"] / f"step_{state['current_step']}_screenshot_{screenshot_count}{refine_suffix}.png"
            
            # Decode and save
            image_bytes = base64.b64decode(screenshot_result["image_data"])
            screenshot_path.write_bytes(image_bytes)
            
            state["screenshot_count"] += 1
            self.display_callback(f"✅ Screenshot saved: {screenshot_path.name}", "success")
            
            # NEW: Vision-based analysis
            try:
                vision_model = ChatAnthropic(model="claude-sonnet-4-20250514", max_tokens=512)
                
                current_step_desc = state["planning_steps"][state["current_step"]] if state["current_step"] < len(state["planning_steps"]) else "Final step"
                
                vision_prompt = f"""Analyze this 3D modeling screenshot from Blender.

Current Step ({state['current_step'] + 1}): {current_step_desc}

CRITICAL VISUAL ANALYSIS - Evaluate:

1. **Geometry Quality**: Does the geometry match the step description?
2. **Detail & Complexity**: Is there sufficient detail and complexity?
3. **Visibility & Occlusion**: Are any objects hidden, overshadowed, or blocked by other objects?
   - Check if newly created objects are visible or hidden behind existing geometry
   - Identify if objects are too close together causing visual clutter
   - Note if important features are obscured from view
4. **Spatial Layout**: Are objects properly spaced and positioned?
5. **Visual Errors**: Any missing elements, malformed geometry, or rendering artifacts?
6. **Overall Quality**: Rate 1-10 with detailed reasoning

**IMPORTANT**: If objects are occluding each other or new geometry is hidden, this is a CRITICAL issue that requires refinement.

Provide analysis with specific focus on visibility and occlusion problems."""
                
                # Create vision message with image
                vision_message = HumanMessage(
                    content=[
                        {"type": "text", "text": vision_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{screenshot_result['image_data']}"},
                        },
                    ]
                )
                
                vision_response = await invoke_with_retry(vision_model, [vision_message])
                vision_feedback = vision_response.content
                
                # Store vision feedback
                if "vision_feedback" not in state:
                    state["vision_feedback"] = []
                state["vision_feedback"].append(vision_feedback)
                
                logger.info(f"Vision Analysis: {vision_feedback[:200]}...")
                self.display_callback("🔍 Vision analysis complete", "success")
                
            except Exception as e:
                logger.error(f"Vision analysis failed: {e}")
                self.display_callback(f"⚠️ Vision analysis failed: {e}", "error")
            
            # Get scene info for feedback
            scene_info = await self.mcp.call_tool("get_scene_info", {})
            feedback = f"Step {state['current_step']} - Scene: {scene_info.get('result', 'Unknown')[:200]}"
            state["feedback_history"].append(feedback)
        else:
            self.display_callback("❌ Screenshot capture failed", "error")
        
        return state
    
    @traceable(name="evaluate_modeling_progress")
    def _evaluate_progress_node(self, state: AgentState) -> AgentState:
        """Evaluate whether modeling is complete with quality check"""
        logger = logging.getLogger(__name__)
        self.display_callback("Evaluating progress...", "thinking")
        
        logger.info(f"Evaluating progress - current_step: {state['current_step']}, total_steps: {len(state['planning_steps'])}")
        
        # Check if all steps are done
        if state["current_step"] >= len(state["planning_steps"]):
            # ENHANCED: Check quality before marking complete
            if state.get("vision_feedback"):
                # Analyze recent vision feedback for quality issues
                recent_feedback = state["vision_feedback"][-2:] if len(state["vision_feedback"]) >= 2 else state["vision_feedback"]
                combined_feedback = "\n\n".join(recent_feedback)
                
                # Check for common quality issues
                quality_issues = []
                if "error" in combined_feedback.lower():
                    quality_issues.append("execution errors detected")
                if "missing" in combined_feedback.lower():
                    quality_issues.append("missing elements")
                if "basic" in combined_feedback.lower() or "simple" in combined_feedback.lower():
                    quality_issues.append("lacks detail or decoration")
                
                if quality_issues:
                    logger.warning(f"Quality issues detected: {', '.join(quality_issues)}")
                    self.display_callback(f"⚠️ Quality issues: {', '.join(quality_issues)}", "info")
            
            state["is_complete"] = True
            logger.info("All steps completed, marking task as complete")
            self.display_callback("All steps completed!", "success")
        else:
            remaining = len(state["planning_steps"]) - state["current_step"]
            logger.info(f"{remaining} steps remaining")
            self.display_callback(f"{remaining} steps remaining", "info")
        
        return state
    
    @traceable(name="assess_step_quality")
    async def _assess_quality_node(self, state: AgentState) -> AgentState:
        """Assess quality of current step using vision feedback"""
        logger = logging.getLogger(__name__)
        self.display_callback("🎯 Assessing quality...", "thinking")
        
        # Initialize quality tracking if needed
        if "quality_scores" not in state:
            state["quality_scores"] = []
        if "refinement_attempts" not in state:
            state["refinement_attempts"] = 0
        if "max_refinements_per_step" not in state:
            # Load from environment (.env already processed by load_dotenv)
            raw_refinements = os.getenv("REFINEMENT_STEPS", "2")
            try:
                max_refinements = int(raw_refinements)
            except ValueError:
                max_refinements = 2  # fallback
            # Ensure non-negative
            state["max_refinements_per_step"] = max(0, max_refinements)
        
        # Get most recent vision feedback
        vision_feedback = state.get("vision_feedback", [])[-1] if state.get("vision_feedback") else ""
        
        if not vision_feedback:
            logger.warning("No vision feedback available, skipping quality assessment")
            state["needs_refinement"] = False
            return state
        
        # Parse quality score from vision feedback
        quality_score = 5  # Default medium score
        try:
            # Look for rating pattern like "8/10" or "rating: 7"
            import re
            score_match = re.search(r'(\d+)\s*/\s*10|rating[:\s]+(\d+)', vision_feedback.lower())
            if score_match:
                quality_score = int(score_match.group(1) or score_match.group(2))
        except Exception as e:
            logger.warning(f"Could not parse quality score: {e}")
        
        # Check for occlusion/visibility issues in feedback (critical problem)
        occlusion_detected = any([
            "hidden" in vision_feedback.lower(),
            "occluded" in vision_feedback.lower(),
            "obscured" in vision_feedback.lower(),
            "blocked" in vision_feedback.lower(),
            "overshadow" in vision_feedback.lower(),
            "behind" in vision_feedback.lower() and "object" in vision_feedback.lower(),
            "not visible" in vision_feedback.lower(),
            "can't see" in vision_feedback.lower() or "cannot see" in vision_feedback.lower()
        ])
        
        # Determine if refinement is needed based on step type
        # Critical steps (1-5) have higher threshold
        if state["current_step"] < 5:
            refinement_threshold = 7  # Critical steps need 7+
            needs_refinement = quality_score < refinement_threshold or occlusion_detected
        else:
            refinement_threshold = 6  # Normal steps need 6+
            needs_refinement = quality_score < refinement_threshold or occlusion_detected
        
        # Log occlusion detection
        if occlusion_detected:
            logger.warning(f"⚠️ Occlusion detected in step {state['current_step']}: Objects may be hidden or overshadowing each other")
            self.display_callback(f"⚠️ Occlusion detected - objects may be hidden", "warning")
        
        # IMPORTANT: Don't refine if we've hit max attempts (this overrides everything)
        if state["refinement_attempts"] >= state["max_refinements_per_step"]:
            if needs_refinement:
                logger.warning(f"⚠️ Max refinement attempts ({state['max_refinements_per_step']}) reached for step {state['current_step']}")
                self.display_callback(f"⚠️ Max refinements reached (score: {quality_score}/10), accepting current result", "warning")
            needs_refinement = False  # Force accept even if score is low
        
        # Store quality assessment
        quality_data = {
            "step": state["current_step"],
            "score": quality_score,
            "needs_refinement": needs_refinement,
            "attempt": state["refinement_attempts"],
            "feedback": vision_feedback[:150]
        }
        state["quality_scores"].append(quality_data)
        state["needs_refinement"] = needs_refinement
        
        if needs_refinement:
            state["refinement_feedback"] = vision_feedback
            self.display_callback(f"🔄 Quality score: {quality_score}/10 (threshold: {refinement_threshold}) - Refinement needed", "info")
            logger.info(f"Step {state['current_step']} needs refinement (score: {quality_score}/{refinement_threshold}, attempt: {state['refinement_attempts']})")
        else:
            state["refinement_feedback"] = None
            state["refinement_attempts"] = 0  # Reset for next step
            self.display_callback(f"✅ Quality score: {quality_score}/10 (threshold: {refinement_threshold}) - Acceptable", "success")
            logger.info(f"Step {state['current_step']} quality acceptable (score: {quality_score}/{refinement_threshold})")
        
        return state
    
    @traceable(name="refine_current_step")
    async def _refine_step_node(self, state: AgentState) -> AgentState:
        """Refine current step based on quality feedback"""
        logger = logging.getLogger(__name__)
        
        state["refinement_attempts"] = state.get("refinement_attempts", 0) + 1
        self.display_callback(f"🔧 Refining step {state['current_step']} (attempt {state['refinement_attempts']})...", "thinking")
        
        # Get current step description
        current_step_desc = state["planning_steps"][state["current_step"]] if state["current_step"] < len(state["planning_steps"]) else "Final step"
        
        # Create refinement prompt
        refinement_prompt = f"""You previously executed this step:
{current_step_desc}

Vision analysis identified these quality issues:
{state.get('refinement_feedback', 'Quality issues detected')}

Generate improved Blender Python code to address these issues. Focus on:
1. **Occlusion & Visibility**: If objects are hidden/overshadowed, reposition or scale them for better visibility
2. **Spatial Layout**: Ensure proper spacing between objects to prevent visual clutter
3. **Detail & Complexity**: Add more detail and complexity to geometry
4. **Geometry Errors**: Fix any malformed or missing geometry
5. **Visual Realism**: Improve overall visual quality
6. **Scene Compatibility**: Maintain compatibility with existing scene objects

**CRITICAL**: If vision feedback mentions occlusion, hidden objects, or visibility issues:
- Move occluded objects to visible positions
- Adjust object scales to prevent overshadowing
- Reposition camera-facing geometry for better view
- Ensure new objects don't block existing important elements

Use the execute_blender_code tool to apply improvements.

{BLENDER_COMPAT_CODE}

IMPORTANT: The code should ENHANCE the existing work, not replace it entirely unless necessary."""
        
        # Create message for LLM
        messages = [
            SystemMessage(content="You are an expert 3D modeler refining Blender scenes based on visual feedback."),
            HumanMessage(content=refinement_prompt)
        ]
        
        # Get tool schemas for Claude (same as execute_step_node)
        tools = self.mcp.get_tools_schema()
        
        try:
            response = await invoke_with_retry(self.llm.bind_tools(tools), messages)
            
            # Execute tool calls
            if hasattr(response, 'tool_calls') and response.tool_calls:
                self.display_callback(f"  🔧 Executing refinement code...", "info")
                
                for tool_call in response.tool_calls:
                    logger.info(f"Refinement calling tool: {tool_call['name']}")
                    
                    result = await self.mcp.call_tool(
                        tool_call['name'],
                        tool_call.get('args', {})
                    )
                    
                    if result.get('success'):
                        self.display_callback(f"  ✅ Refinement applied", "success")
                    else:
                        self.display_callback(f"  ⚠️ Refinement had issues: {result.get('result', '')[:100]}", "error")
                        logger.warning(f"Refinement tool result: {result}")
            else:
                logger.warning("LLM did not generate refinement tool calls")
                self.display_callback("⚠️ No refinement actions generated", "info")
        
        except Exception as e:
            logger.error(f"Refinement execution failed: {e}")
            self.display_callback(f"❌ Refinement failed: {e}", "error")
        
        return state
    
    def _should_refine(self, state: AgentState) -> str:
        """Decide whether to refine current step or continue"""
        # Check if refinement is enabled at all
        if not state.get("enable_refinement", True):
            return "continue"  # Skip refinement entirely if disabled
        
        if state.get("needs_refinement", False):
            return "refine"
        return "continue"
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue or complete"""
        # Check for critical errors first
        if state.get("critical_error"):
            self.logger.critical(f"Workflow halted due to critical error: {state['critical_error']}")
            return "complete"  # End workflow on critical error
        return "complete" if state["is_complete"] else "continue"
    
    @traceable(name="complete_modeling")
    def _complete_node(self, state: AgentState) -> AgentState:
        """Finalize the modeling process"""
        self.display_callback("Modeling complete!", "success")
        self.display_callback(f"Total screenshots: {state['screenshot_count']}", "info")
        self.display_callback(f"Screenshots saved in: {state['screenshot_dir']}", "info")
        
        state["messages"].append(AIMessage(content="3D modeling task completed successfully"))
        return state
    
    @staticmethod
    def generate_session_id(requirement_json_path: str) -> str:
        """Generate deterministic session ID from input file path"""
        # Use hash of absolute path to ensure same ID for same file
        abs_path = str(Path(requirement_json_path).resolve())
        hash_obj = hashlib.sha256(abs_path.encode())
        return hash_obj.hexdigest()[:16]  # Use first 16 chars of hash
    
    @traceable(name="run_modeling_task")
    async def run(self, requirement_json_path: str, use_deterministic_session: bool = True) -> Dict[str, Any]:
        """
        Run the modeling task from a JSON requirement file
        
        Args:
            requirement_json_path: Path to JSON file with refined_prompt
            use_deterministic_session: Use file-based session ID for resume capability
            
        Returns:
            Dictionary with results
        """
        self.display_callback(f"Loading requirement from: {requirement_json_path}", "info")
        
        # Load requirement
        with open(requirement_json_path, 'r') as f:
            requirement_data = json.load(f)
        
        refined_prompt = requirement_data.get("refined_prompt")
        if not refined_prompt:
            raise ValueError("No 'refined_prompt' found in JSON file")
        
        # Load refinement setting (default to True for backward compatibility)
        enable_refinement = requirement_data.get("enable_refinement_steps", True)
        
        self.display_callback(f"Requirement loaded: {len(refined_prompt)} characters", "success")
        self.display_callback(f"Refinement steps: {'Enabled ✅' if enable_refinement else 'Disabled ⚠️'}", "info")
        
        # Override session ID with deterministic one if requested
        if use_deterministic_session:
            original_session_id = self.session_id
            self.session_id = self.generate_session_id(requirement_json_path)
            if original_session_id != self.session_id:
                self.display_callback(f"Using deterministic session ID: {self.session_id}", "info")
                self.display_callback("This allows resuming from previous runs of the same file", "info")
        
        # Create screenshot directory
        screenshot_dir = Path("data/blender/screenshots") / self.session_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        initial_state: AgentState = {
            "messages": [HumanMessage(content=f"Create 3D model: {refined_prompt[:200]}...")],
            "requirement": refined_prompt,
            "session_id": self.session_id,
            "screenshot_dir": screenshot_dir,
            "tool_results": [],
            "screenshot_count": 0,
            "planning_steps": [],
            "current_step": 0,
            "is_complete": False,
            "feedback_history": [],
            "initial_scene_state": {},
            "completed_steps": [],
            "is_resuming": False,
            "enable_refinement": enable_refinement
        }
        
        # Run the graph
        # Set high recursion limit for multi-step workflows
        # Each step goes through: plan → execute → capture → assess → evaluate → (loop)
        # For complex models with refinement loops, we need higher limits
        recursion_limit = int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "100"))
        
        config = {
            "configurable": {"thread_id": self.session_id},
            "recursion_limit": recursion_limit
        }
        
        self.display_callback(f"Starting modeling workflow with recursion limit: {recursion_limit}...", "info")
        logger = logging.getLogger(__name__)
        logger.info(f"LangGraph recursion limit set to: {recursion_limit}")
        
        final_state = None
        recursion_limit_reached = False
        
        try:
            final_state = await self.graph.ainvoke(initial_state, config)
        except GraphRecursionError as e:
            # Gracefully handle recursion limit
            recursion_limit_reached = True
            logger.warning(f"Recursion limit of {recursion_limit} reached. Saving partial progress...")
            self.display_callback(f"⚠️ Recursion limit reached ({recursion_limit} iterations). Partial progress saved.", "info")
            
            # Get the last available state from the graph's checkpointer
            # The state is automatically saved by LangGraph's checkpointer
            try:
                # Try to get the last checkpoint state
                from langgraph.checkpoint.base import CheckpointTuple
                checkpoints = list(self.memory.list(config))
                if checkpoints:
                    # Get the most recent checkpoint
                    latest_checkpoint = checkpoints[0]
                    final_state = latest_checkpoint.checkpoint.get("channel_values", {})
                    logger.info(f"Retrieved checkpoint state with {final_state.get('current_step', 0)} steps completed")
                else:
                    # Fallback to initial state if no checkpoints
                    logger.warning("No checkpoints found, using initial state")
                    final_state = initial_state
            except Exception as checkpoint_error:
                logger.error(f"Error retrieving checkpoint: {checkpoint_error}")
                # Use initial state as fallback
                final_state = initial_state
        
        # Prepare results
        if final_state:
            is_complete = final_state.get("is_complete", False) and not recursion_limit_reached
            
            results = {
                "session_id": self.session_id,
                "requirement": refined_prompt,
                "steps_executed": final_state.get("current_step", 0),
                "total_steps": len(final_state.get("planning_steps", [])),
                "screenshots_captured": final_state.get("screenshot_count", 0),
                "screenshot_directory": str(screenshot_dir),
                "success": is_complete,
                "partial_completion": recursion_limit_reached,
                "can_resume": recursion_limit_reached or not is_complete,
                "tool_results": final_state.get("tool_results", []),
                "recursion_limit_reached": recursion_limit_reached
            }
            
            if recursion_limit_reached:
                steps_completed = final_state.get("current_step", 0)
                total_steps = len(final_state.get("planning_steps", []))
                remaining = total_steps - steps_completed
                
                self.display_callback(
                    f"⚠️ Workflow paused at step {steps_completed}/{total_steps}. "
                    f"{remaining} steps remaining. Use resume mode to continue.",
                    "info"
                )
                logger.info(f"Partial results: {steps_completed}/{total_steps} steps completed")
            else:
                self.display_callback("✅ Workflow complete!", "success")
        else:
            # Fallback if state retrieval completely failed
            results = {
                "session_id": self.session_id,
                "requirement": refined_prompt,
                "steps_executed": 0,
                "total_steps": 0,
                "screenshots_captured": 0,
                "screenshot_directory": str(screenshot_dir),
                "success": False,
                "partial_completion": True,
                "can_resume": True,
                "tool_results": [],
                "recursion_limit_reached": recursion_limit_reached,
                "error": "Failed to retrieve workflow state after recursion limit"
            }
            self.display_callback("⚠️ Workflow interrupted. State could not be recovered.", "error")
        
        return results
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.mcp.cleanup()
        except Exception:
            # Suppress all cleanup errors
            pass
