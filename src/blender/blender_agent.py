"""
Blender Chat Agent
Handles MCP connection and Claude API interactions for Blender control
"""
import os
import asyncio
import base64
import time
from typing import Dict, List, Any
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Rate limit configuration from environment
RATE_LIMIT_MAX_RETRIES = int(os.getenv("RATE_LIMIT_MAX_RETRIES", "5"))
RATE_LIMIT_BASE_WAIT = int(os.getenv("RATE_LIMIT_BASE_WAIT", "15"))  # seconds


def call_claude_with_retry(anthropic_client, **kwargs):
    """
    Call Claude API with exponential backoff for rate limits
    
    Uses exponential backoff: 15s, 30s, 60s, 120s, 240s
    """
    max_retries = RATE_LIMIT_MAX_RETRIES
    base_wait = RATE_LIMIT_BASE_WAIT
    
    for attempt in range(max_retries):
        try:
            return anthropic_client.messages.create(**kwargs)
        except Exception as e:
            error_str = str(e).lower()
            is_rate_limit = "rate_limit" in error_str or "429" in error_str or "overloaded" in error_str
            
            if is_rate_limit and attempt < max_retries - 1:
                # Exponential backoff: 15s, 30s, 60s, 120s, 240s
                wait_time = base_wait * (2 ** attempt)
                
                print(
                    f"⏳ Rate limit hit (attempt {attempt + 1}/{max_retries}). "
                    f"Waiting {wait_time}s before retry..."
                )
                
                time.sleep(wait_time)
            else:
                # Not a rate limit error or out of retries
                raise


class BlenderChatAgent:
    """Agent for managing Blender MCP connection and Claude AI interactions"""
    
    def __init__(self, api_key: str = None, mcp_host: str = "localhost", mcp_port: int = 9876):
        self.conversation_history: List[Dict[str, Any]] = []
        self.mcp_session = None
        self.tools: Dict[str, Any] = {}
        self.anthropic = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.mcp_host = mcp_host
        self.mcp_port = mcp_port
        self.stdio_context = None
        self.session_context = None
        self._cleanup_done = False
        
    async def initialize_mcp(self) -> int:
        """Initialize MCP connection to Blender"""
        # Get the absolute path to main.py
        main_py_path = os.path.join(os.getcwd(), "main.py")
        
        # Pass environment variables to subprocess, including user-specific Blender port
        env = os.environ.copy()
        env["BLENDER_HOST"] = self.mcp_host
        env["BLENDER_PORT"] = str(self.mcp_port)
        
        server_params = StdioServerParameters(
            command="python",
            args=[main_py_path],
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
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self._cleanup_done:
            return
        
        try:
            if self.session_context:
                try:
                    await self.session_context.__aexit__(None, None, None)
                except Exception:
                    pass
            if self.stdio_context:
                try:
                    await self.stdio_context.__aexit__(None, None, None)
                except Exception:
                    pass
        finally:
            self._cleanup_done = True
            self.mcp_session = None
            self.session_context = None
            self.stdio_context = None
    
    def format_tools_for_claude(self) -> List[Dict[str, Any]]:
        """Convert MCP tools to Claude's tool format"""
        claude_tools = []
        for tool_name, tool in self.tools.items():
            claude_tool = {
                "name": tool_name,
                "description": tool.description or f"Execute {tool_name}",
                "input_schema": tool.inputSchema or {"type": "object", "properties": {}}
            }
            claude_tools.append(claude_tool)
        return claude_tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Call an MCP tool and return the result"""
        try:
            print(f"🔧 Calling tool: {tool_name}")
            print(f"   Arguments: {arguments}")
            
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            # Extract text and images from result
            result_text = ""
            image_data = None
            
            for content in result.content:
                if hasattr(content, 'text'):
                    result_text += content.text
                elif hasattr(content, 'data') and hasattr(content, 'mimeType'):
                    # Handle image data
                    if content.mimeType.startswith('image/'):
                        # Check if data is already bytes or a string
                        if isinstance(content.data, bytes):
                            # Convert binary data to base64
                            image_data = base64.b64encode(content.data).decode('utf-8')
                        else:
                            # Already base64 string
                            image_data = content.data
                        result_text += f'\n[Image: data:{content.mimeType};base64,{image_data}]'
                else:
                    result_text += str(content)
            
            print(f"✅ Tool completed: {tool_name}")
            if image_data:
                print(f"   Captured image: {len(image_data)} bytes")
            
            return {
                "success": True,
                "result": result_text,
                "tool_name": tool_name,
                "arguments": arguments,
                "image_data": image_data
            }
        except Exception as e:
            error_msg = f"Error calling {tool_name}: {str(e)}"
            print(f"❌ Tool failed: {tool_name} - {str(e)}")
            return {
                "success": False,
                "result": error_msg,
                "tool_name": tool_name,
                "arguments": arguments
            }

    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Send a message to Claude and execute any tool calls"""
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        print(f"\n💬 Sending message to Claude...")
        
        # System prompt
        system_prompt = """You are an AI assistant that helps users create 3D scenes in Blender.

You have access to MCP tools that control Blender. When users ask you to create objects, modify scenes, or perform any Blender operations, use the available tools to accomplish their requests.

Guidelines:
1. Always check the scene first with get_scene_info when starting a new request
2. Use execute_blender_code for creating objects, modifying properties, setting up cameras, lighting, etc.
3. CRITICAL: After creating or modifying any objects, ALWAYS call capture_screenshot to show the user the result
4. Break complex requests into smaller steps
5. Check integration status (PolyHaven, Hyper3D, Sketchfab) before using those features
6. Provide clear explanations of what you're doing
7. If something fails, explain the error and suggest alternatives

Be conversational and helpful. Execute the user's requests step by step. Remember: ALWAYS capture a screenshot after creating/modifying objects so users can see their work."""
        
        # Prepare tools for Claude
        claude_tools = self.format_tools_for_claude()
        
        responses = []
        tool_calls = []
        
        # Call Claude with tool use capability
        print(f"🤖 Waiting for Claude's response...")
        response = call_claude_with_retry(
            self.anthropic,
            # model="claude-3-haiku-20240307", 
            model="claude-sonnet-4-5-20250929",
            max_tokens=4096,
            system=system_prompt,
            tools=claude_tools,
            messages=self.conversation_history
        )
        
        print(f"📨 Received response from Claude")
        
        # Process response and tool calls
        assistant_message = {"role": "assistant", "content": []}
        
        for content_block in response.content:
            if content_block.type == "text":
                print(f"💭 Claude says: {content_block.text[:100]}...")
                responses.append(content_block.text)
                assistant_message["content"].append(content_block)
            
            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                print(f"\n🔨 Claude wants to use tool: {tool_name}")
                
                # Execute the MCP tool
                tool_result = await self.call_mcp_tool(tool_name, tool_input)
                tool_calls.append(tool_result)
                
                # Add tool use to message
                assistant_message["content"].append(content_block)
                
                # Create tool result message for Claude
                # If result contains image data, send a summary instead of full base64
                result_for_claude = tool_result["result"]
                if tool_result.get("image_data"):
                    # Replace the embedded base64 with a placeholder
                    result_for_claude = f"Screenshot captured successfully. Image size: {len(tool_result['image_data'])} bytes (base64 encoded)"
                
                self.conversation_history.append(assistant_message)
                
                # If we just executed code to create/modify objects, remind Claude to capture screenshot
                screenshot_reminder = ""
                if tool_name == "execute_blender_code" and "bpy.ops.mesh" in str(tool_input):
                    screenshot_reminder = "\n\nREMINDER: You MUST now call capture_screenshot to show the user the result."
                
                self.conversation_history.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": result_for_claude + screenshot_reminder
                    }]
                })
                
                # Keep calling Claude until it stops requesting tools
                while True:
                    print(f"🤖 Getting Claude's follow-up response...")
                    follow_up = call_claude_with_retry(
                        self.anthropic,
                        model="claude-sonnet-4-5-20250929",
                        max_tokens=4096,
                        system=system_prompt,
                        tools=claude_tools,
                        messages=self.conversation_history
                    )
                    
                    print(f"📨 Received follow-up response from Claude")
                    
                    # Check if response has more tool calls
                    has_tool_calls = any(block.type == "tool_use" for block in follow_up.content)
                    
                    if not has_tool_calls:
                        # Just text response, we're done
                        assistant_message = {"role": "assistant", "content": []}
                        for block in follow_up.content:
                            if block.type == "text":
                                responses.append(block.text)
                                assistant_message["content"].append(block)
                        break
                    
                    # Process all tool calls in this response
                    assistant_message = {"role": "assistant", "content": []}
                    for block in follow_up.content:
                        if block.type == "text":
                            responses.append(block.text)
                            assistant_message["content"].append(block)
                        elif block.type == "tool_use":
                            print(f"\n🔨 Claude wants to use tool: {block.name}")
                            
                            # Add tool use to assistant message
                            assistant_message["content"].append(block)
                            
                            # Execute the tool
                            tool_result = await self.call_mcp_tool(block.name, block.input)
                            tool_calls.append(tool_result)
                    
                    # Add assistant message with all tool uses
                    self.conversation_history.append(assistant_message)
                    
                    # Add tool results for ALL tools in this message
                    for block in follow_up.content:
                        if block.type == "tool_use":
                            # Find the corresponding result
                            tool_result = next((t for t in tool_calls if t.get("tool_name") == block.name), tool_calls[-1])
                            
                            result_for_claude = tool_result["result"]
                            if tool_result.get("image_data"):
                                result_for_claude = f"Screenshot captured successfully. Image size: {len(tool_result['image_data'])} bytes (base64 encoded)"
                            
                            # Check if screenshot reminder needed
                            screenshot_reminder = ""
                            if block.name == "execute_blender_code" and "bpy.ops.mesh" in str(block.input):
                                screenshot_reminder = "\n\nREMINDER: You MUST now call capture_screenshot to show the user the result."
                            
                            self.conversation_history.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": block.id,
                                    "content": result_for_claude + screenshot_reminder
                                }]
                            })
        
        # Add final assistant message to history
        if assistant_message["content"]:
            self.conversation_history.append(assistant_message)
        
        return {
            "responses": responses,
            "tool_calls": tool_calls
        }
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history"""
        return self.conversation_history
    
    def clear_conversation_history(self):
        """Clear the conversation history"""
        self.conversation_history = []
