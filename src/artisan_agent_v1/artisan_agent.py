"""
Artisan Agent - Autonomous 3D Modeling Agent for Blender
Uses LangGraph for reasoning and sequential tool execution
"""
import os
import asyncio
import base64
import json
import logging
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

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Load environment variables
load_dotenv()

# Configure LangSmith
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "true"


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
        server_params = StdioServerParameters(
            command="python",
            args=["main.py"],
            env=None
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
    
    def __init__(self, session_id: Optional[str] = None, display_callback: Optional[callable] = None):
        """
        Initialize the Artisan Agent
        
        Args:
            session_id: Optional session ID (generated if not provided)
            display_callback: Optional callback for displaying progress (for Streamlit)
        """
        self.session_id = session_id or str(uuid4())
        self.display_callback = display_callback or self._console_display
        
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
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("execute_step", self._execute_step_node)
        workflow.add_node("capture_feedback", self._capture_feedback_node)
        workflow.add_node("evaluate_progress", self._evaluate_progress_node)
        workflow.add_node("complete", self._complete_node)
        
        # Set entry point
        workflow.set_entry_point("plan")
        
        # Add edges
        workflow.add_edge("plan", "execute_step")
        workflow.add_edge("execute_step", "capture_feedback")
        workflow.add_edge("capture_feedback", "evaluate_progress")
        
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
    
    @traceable(name="plan_modeling_steps")
    def _plan_node(self, state: AgentState) -> AgentState:
        """Plan the steps needed to complete the 3D modeling task"""
        logger = logging.getLogger(__name__)
        self.display_callback("Planning modeling steps...", "plan")
        
        planning_prompt = f"""You are an expert 3D modeling planner for Blender. 
        
Given this modeling requirement, break it down into sequential, actionable steps.
Each step should be a specific Blender operation that can be executed.

Requirement:
{state['requirement'][:1000]}...

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
        
        state["planning_steps"] = steps
        state["current_step"] = 0
        state["messages"].append(AIMessage(content=f"Created plan with {len(steps)} steps"))
        
        self.display_callback(f"Created {len(steps)}-step plan", "success")
        for i, step in enumerate(steps[:5], 1):  # Show first 5 steps
            self.display_callback(f"  {i}. {step[:100]}", "plan")
        if len(steps) > 5:
            self.display_callback(f"  ... and {len(steps) - 5} more steps", "plan")
        
        return state
    
    @traceable(name="execute_modeling_step")
    async def _execute_step_node(self, state: AgentState) -> AgentState:
        """Execute the current modeling step"""
        logger = logging.getLogger(__name__)
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
{chr(10).join(state['feedback_history'][-3:]) if state['feedback_history'] else 'Starting fresh'}

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
                
                if result["success"]:
                    self.display_callback(f"  ✅ {tool_call['name']} completed", "success")
                else:
                    logger.error(f"Tool {tool_call['name']} failed: {result['result'][:200]}")
                    self.display_callback(f"  ❌ {tool_call['name']} failed: {result['result'][:100]}", "error")
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
        """Capture viewport screenshot for visual feedback"""
        self.display_callback("Capturing viewport screenshot...", "screenshot")
        
        # Call screenshot tool
        screenshot_result = await self.mcp.call_tool("get_viewport_screenshot", {"max_size": 800})
        
        if screenshot_result["success"] and screenshot_result.get("image_data"):
            # Save screenshot
            screenshot_count = state["screenshot_count"]
            screenshot_path = state["screenshot_dir"] / f"step_{state['current_step']}_screenshot_{screenshot_count}.png"
            
            # Decode and save
            image_bytes = base64.b64decode(screenshot_result["image_data"])
            screenshot_path.write_bytes(image_bytes)
            
            state["screenshot_count"] += 1
            self.display_callback(f"Screenshot saved: {screenshot_path.name}", "success")
            
            # Get scene info for feedback
            scene_info = await self.mcp.call_tool("get_scene_info", {})
            feedback = f"Step {state['current_step']} - Scene: {scene_info.get('result', 'Unknown')[:200]}"
            state["feedback_history"].append(feedback)
        else:
            self.display_callback("Screenshot capture failed", "error")
        
        return state
    
    @traceable(name="evaluate_modeling_progress")
    def _evaluate_progress_node(self, state: AgentState) -> AgentState:
        """Evaluate whether modeling is complete"""
        logger = logging.getLogger(__name__)
        self.display_callback("Evaluating progress...", "thinking")
        
        logger.info(f"Evaluating progress - current_step: {state['current_step']}, total_steps: {len(state['planning_steps'])}")
        
        # Check if all steps are done
        if state["current_step"] >= len(state["planning_steps"]):
            state["is_complete"] = True
            logger.info("All steps completed, marking task as complete")
            self.display_callback("All steps completed!", "success")
        else:
            remaining = len(state["planning_steps"]) - state["current_step"]
            logger.info(f"{remaining} steps remaining")
            self.display_callback(f"{remaining} steps remaining", "info")
        
        return state
    
    def _should_continue(self, state: AgentState) -> str:
        """Decide whether to continue or complete"""
        return "complete" if state["is_complete"] else "continue"
    
    @traceable(name="complete_modeling")
    def _complete_node(self, state: AgentState) -> AgentState:
        """Finalize the modeling process"""
        self.display_callback("Modeling complete!", "success")
        self.display_callback(f"Total screenshots: {state['screenshot_count']}", "info")
        self.display_callback(f"Screenshots saved in: {state['screenshot_dir']}", "info")
        
        state["messages"].append(AIMessage(content="3D modeling task completed successfully"))
        return state
    
    @traceable(name="run_modeling_task")
    async def run(self, requirement_json_path: str) -> Dict[str, Any]:
        """
        Run the modeling task from a JSON requirement file
        
        Args:
            requirement_json_path: Path to JSON file with refined_prompt
            
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
        
        self.display_callback(f"Requirement loaded: {len(refined_prompt)} characters", "success")
        
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
            "feedback_history": []
        }
        
        # Run the graph
        # Set high recursion limit for multi-step workflows
        # Each step goes through: plan → execute → capture → evaluate → (loop)
        # For 12 steps, we need ~50+ iterations, so set to 100 to be safe
        config = {
            "configurable": {"thread_id": self.session_id},
            "recursion_limit": int(os.getenv("LANGGRAPH_RECURSION_LIMIT", "100"))
        }
        
        self.display_callback("Starting modeling workflow...", "info")
        
        final_state = await self.graph.ainvoke(initial_state, config)
        
        # Prepare results
        results = {
            "session_id": self.session_id,
            "requirement": refined_prompt,
            "steps_executed": final_state["current_step"],
            "screenshots_captured": final_state["screenshot_count"],
            "screenshot_directory": str(screenshot_dir),
            "success": final_state["is_complete"],
            "tool_results": final_state["tool_results"]
        }
        
        self.display_callback("Workflow complete!", "success")
        
        return results
    
    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.mcp.cleanup()
        except Exception:
            # Suppress all cleanup errors
            pass
