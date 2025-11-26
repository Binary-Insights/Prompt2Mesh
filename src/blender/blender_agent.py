"""
Blender Chat Agent
Handles MCP connection and Claude API interactions for Blender control
"""
import os
import asyncio
import base64
from typing import Dict, List, Any
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class BlenderChatAgent:
    """Agent for managing Blender MCP connection and Claude AI interactions"""
    
    def __init__(self, api_key: str = None):
        self.conversation_history: List[Dict[str, Any]] = []
        self.mcp_session = None
        self.tools: Dict[str, Any] = {}
        self.anthropic = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self.stdio_context = None
        self.session_context = None
        self._cleanup_done = False
        
    async def initialize_mcp(self) -> int:
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
                        # Convert binary data to base64
                        image_data = base64.b64encode(content.data).decode('utf-8')
                        result_text += f'\n[Image: data:{content.mimeType};base64,{image_data}]'
                else:
                    result_text += str(content)
            
            return {
                "success": True,
                "result": result_text,
                "tool_name": tool_name,
                "arguments": arguments,
                "image_data": image_data
            }
        except Exception as e:
            error_msg = f"Error calling {tool_name}: {str(e)}"
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
        
        # System prompt
        system_prompt = """You are an AI assistant that helps users create 3D scenes in Blender.

You have access to MCP tools that control Blender. When users ask you to create objects, modify scenes, or perform any Blender operations, use the available tools to accomplish their requests.

Guidelines:
1. Always check the scene first with get_scene_info when starting a new request
2. Use execute_blender_code for creating objects, modifying properties, setting up cameras, lighting, etc.
3. Break complex requests into smaller steps
4. Check integration status (PolyHaven, Hyper3D, Sketchfab) before using those features
5. Provide clear explanations of what you're doing
6. If something fails, explain the error and suggest alternatives

Be conversational and helpful. Execute the user's requests step by step."""
        
        # Prepare tools for Claude
        claude_tools = self.format_tools_for_claude()
        
        responses = []
        tool_calls = []
        
        # Call Claude with tool use capability
        response = self.anthropic.messages.create(
            model="claude-3-haiku-20240307", 
            max_tokens=4096,
            system=system_prompt,
            tools=claude_tools,
            messages=self.conversation_history
        )
        
        # Process response and tool calls
        assistant_message = {"role": "assistant", "content": []}
        
        for content_block in response.content:
            if content_block.type == "text":
                responses.append(content_block.text)
                assistant_message["content"].append(content_block)
            
            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                # Execute the MCP tool
                tool_result = await self.call_mcp_tool(tool_name, tool_input)
                tool_calls.append(tool_result)
                
                # Add tool use to message
                assistant_message["content"].append(content_block)
                
                # Create tool result message
                self.conversation_history.append(assistant_message)
                self.conversation_history.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result["result"]
                    }]
                })
                
                # Get Claude's response after tool execution
                follow_up = self.anthropic.messages.create(
                    model="claude-3-haiku-20240307",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=claude_tools,
                    messages=self.conversation_history
                )
                
                # Process follow-up response
                assistant_message = {"role": "assistant", "content": []}
                for block in follow_up.content:
                    if block.type == "text":
                        responses.append(block.text)
                        assistant_message["content"].append(block)
        
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
