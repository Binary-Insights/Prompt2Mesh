"""
Blender Network Agent
Connects to Blender addon TCP server for Kubernetes deployments
"""
import os
import json
import socket
import asyncio
from typing import Dict, List, Any
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


class BlenderNetworkAgent:
    """Agent that connects to Blender addon's TCP server (port 9876)"""
    
    def __init__(self, api_key: str = None, blender_host: str = None, blender_port: int = None):
        self.conversation_history: List[Dict[str, Any]] = []
        self.tools: Dict[str, Any] = {}
        self.anthropic = Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        self._cleanup_done = False
        
        # Get Blender connection details from environment
        self.blender_host = blender_host or os.environ.get("BLENDER_HOST", "localhost")
        self.blender_port = blender_port or int(os.environ.get("BLENDER_PORT", "9876"))
        self.sock = None
        
    async def initialize_mcp(self) -> int:
        """Initialize connection to Blender addon TCP server"""
        # Test connection with a simple command (don't keep persistent connection)
        try:
            result = await self._send_command("get_scene_info", {})
            if result.get("success"):
                print(f"✅ Successfully connected to Blender at {self.blender_host}:{self.blender_port}")
            else:
                raise ConnectionError(f"Blender connection test failed: {result.get('error', 'Unknown error')}")
        except Exception as e:
            raise ConnectionError(f"Could not connect to Blender at {self.blender_host}:{self.blender_port}: {str(e)}")
        
        # Get available tools from Blender (list_tools might not exist, use defaults)
        result = await self._send_command("list_tools", {})
        if result.get("success", False):
            tools_list = result.get("tools", [])
            self.tools = {tool["name"]: tool for tool in tools_list}
        else:
            # list_tools not available, use default tool set
            self.tools = self._get_default_tools()
        
        return len(self.tools)
    
    async def _send_command(self, command_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send command to Blender and get response"""
        # Create a new socket for each command (server closes connection after response)
        sock = None
        try:
            command = {
                "tool": command_type,  # Server expects 'tool' not 'type'
                "params": params
            }
            
            loop = asyncio.get_event_loop()
            
            # Create new socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10.0)
            
            # Connect
            await loop.run_in_executor(None, sock.connect, (self.blender_host, self.blender_port))
            
            # Send command
            message = json.dumps(command).encode('utf-8')
            await loop.run_in_executor(None, sock.sendall, message)
            
            # Receive response
            response_data = await loop.run_in_executor(None, self._receive_full_response, sock)
            response = json.loads(response_data.decode('utf-8'))
            
            return response
        except Exception as e:
            print(f"❌ Error sending command: {str(e)}")
            return {"status": "error", "message": str(e)}
        finally:
            if sock:
                sock.close()
    
    def _receive_full_response(self, sock) -> bytes:
        """Receive full JSON response from Blender"""
        chunks = []
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            chunks.append(chunk)
            # Try to parse as JSON to see if complete
            try:
                data = b''.join(chunks)
                json.loads(data.decode('utf-8'))
                return data
            except json.JSONDecodeError:
                continue
        return b''.join(chunks)
    
    def _get_default_tools(self) -> Dict[str, Any]:
        """Get default Blender tools"""
        return {
            "get_scene_info": {"name": "get_scene_info", "description": "Get scene information"},
            "create_cube": {"name": "create_cube", "description": "Create a cube"},
            "create_sphere": {"name": "create_sphere", "description": "Create a sphere"},
            "execute_python": {"name": "execute_python", "description": "Execute Python code"},
            "render_screenshot": {"name": "render_screenshot", "description": "Render screenshot"},
        }
    
    async def cleanup(self):
        """Clean up connection"""
        if self._cleanup_done:
            return
        
        try:
            if self.sock:
                self.sock.close()
                self.sock = None
        finally:
            self._cleanup_done = True
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """Get conversation history"""
        return self.conversation_history
    
    def format_tools_for_claude(self) -> List[Dict[str, Any]]:
        """Convert tools to Claude format"""
        claude_tools = []
        for tool_name, tool in self.tools.items():
            claude_tool = {
                "name": tool_name,
                "description": tool.get("description", f"Execute {tool_name}"),
                "input_schema": tool.get("input_schema", {"type": "object", "properties": {}})
            }
            claude_tools.append(claude_tool)
        return claude_tools
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict) -> Dict[str, Any]:
        """Call a Blender tool via TCP"""
        try:
            print(f"🔧 Calling tool: {tool_name}")
            print(f"   Arguments: {arguments}")
            
            result = await self._send_command(tool_name, arguments)
            
            # Check if command was successful (MCP server returns 'success' field)
            if result.get("success", False):
                return {
                    "success": True,
                    "result": json.dumps(result, indent=2),  # Return full result as JSON string
                    "tool_name": tool_name,
                    "arguments": arguments
                }
            else:
                return {
                    "success": False,
                    "result": result.get("error", result.get("message", "Unknown error")),
                    "tool_name": tool_name,
                    "arguments": arguments
                }
        except Exception as e:
            return {
                "success": False,
                "result": f"Error calling {tool_name}: {str(e)}",
                "tool_name": tool_name,
                "arguments": arguments
            }
    
    async def chat(self, user_message: str) -> Dict[str, Any]:
        """Send message to Claude and execute tool calls"""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        print(f"\n💬 Sending message to Claude...")
        
        tool_results = []
        max_turns = 10
        turn = 0
        
        while turn < max_turns:
            turn += 1
            
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                tools=self.format_tools_for_claude(),
                messages=self.conversation_history
            )
            
            if response.stop_reason == "end_turn":
                # Extract final text response
                text_response = ""
                for block in response.content:
                    if hasattr(block, 'text'):
                        text_response += block.text
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                return {
                    "response": text_response,
                    "tool_results": tool_results,
                    "success": True
                }
            
            elif response.stop_reason == "tool_use":
                # Process tool calls
                assistant_content = []
                
                for block in response.content:
                    if hasattr(block, 'text'):
                        assistant_content.append(block)
                    elif block.type == "tool_use":
                        assistant_content.append(block)
                        
                        # Execute tool
                        result = await self.call_mcp_tool(block.name, block.input)
                        tool_results.append(result)
                
                self.conversation_history.append({
                    "role": "assistant",
                    "content": assistant_content
                })
                
                # Add tool results
                tool_result_content = []
                for block in response.content:
                    if block.type == "tool_use":
                        matching_result = next(
                            (r for r in tool_results if r["tool_name"] == block.name),
                            None
                        )
                        if matching_result:
                            tool_result_content.append({
                                "type": "tool_result",
                                "tool_use_id": block.id,
                                "content": matching_result["result"]
                            })
                
                self.conversation_history.append({
                    "role": "user",
                    "content": tool_result_content
                })
            else:
                break
        
        return {
            "response": "Conversation exceeded maximum turns",
            "tool_results": tool_results,
            "success": False
        }
