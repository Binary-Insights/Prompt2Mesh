#!/usr/bin/env python3
"""
AI-Powered Blender Chat Client
Uses Claude API to interpret natural language and control Blender via MCP tools
"""
import os
import sys
import json
import asyncio
from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Anthropic client
anthropic = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

class BlenderChatAgent:
    def __init__(self):
        self.conversation_history = []
        self.mcp_session = None
        self.tools = {}
        
    async def initialize_mcp(self):
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
        
        print(f"✓ Connected to Blender MCP server")
        print(f"✓ Loaded {len(self.tools)} tools\n")
    
    async def cleanup(self):
        """Clean up MCP connection"""
        if self.session_context:
            await self.session_context.__aexit__(None, None, None)
        if self.stdio_context:
            await self.stdio_context.__aexit__(None, None, None)
    
    def format_tools_for_claude(self):
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
    
    async def call_mcp_tool(self, tool_name: str, arguments: dict):
        """Call an MCP tool and return the result"""
        try:
            print(f"  🔧 Executing: {tool_name}")
            if arguments:
                print(f"     Arguments: {json.dumps(arguments, indent=6)}")
            
            result = await self.mcp_session.call_tool(tool_name, arguments)
            
            # Extract text from result
            result_text = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    result_text += content.text
                else:
                    result_text += str(content)
            
            print(f"  ✓ Completed\n")
            return result_text
        except Exception as e:
            error_msg = f"Error calling {tool_name}: {str(e)}"
            print(f"  ✗ {error_msg}\n")
            return error_msg
    
    async def chat(self, user_message: str):
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
        
        print("🤔 Claude is thinking...\n")
        
        # Call Claude with tool use capability - using streaming for real-time output
        with anthropic.messages.stream(
            model="claude-3-haiku-20240307", 
            max_tokens=4096,
            system=system_prompt,
            tools=claude_tools,
            messages=self.conversation_history
        ) as stream:
            # Process streaming response
            assistant_message = {"role": "assistant", "content": []}
            current_text = ""
            
            for event in stream:
                if event.type == "content_block_start":
                    if event.content_block.type == "text":
                        print("💬 Claude: ", end="", flush=True)
                
                elif event.type == "content_block_delta":
                    if hasattr(event.delta, "text"):
                        print(event.delta.text, end="", flush=True)
                        current_text += event.delta.text
                
                elif event.type == "content_block_stop":
                    if current_text:
                        print("\n")  # New line after text
                        current_text = ""
            
            # Get the final message
            response = stream.get_final_message()
        
        # Process response and tool calls
        assistant_message = {"role": "assistant", "content": []}
        
        for content_block in response.content:
            if content_block.type == "text":
                print(f"💬 Claude: {content_block.text}\n")
                assistant_message["content"].append(content_block)
            
            elif content_block.type == "tool_use":
                tool_name = content_block.name
                tool_input = content_block.input
                
                # Execute the MCP tool
                tool_result = await self.call_mcp_tool(tool_name, tool_input)
                
                # Add tool use to message
                assistant_message["content"].append(content_block)
                
                # Create tool result message
                self.conversation_history.append(assistant_message)
                self.conversation_history.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    }]
                })
                
                # Get Claude's response after tool execution
                follow_up = anthropic.messages.create(
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
                        print(f"💬 Claude: {block.text}\n")
                        assistant_message["content"].append(block)
        
        # Add final assistant message to history
        if assistant_message["content"]:
            self.conversation_history.append(assistant_message)

async def main():
    """Main interactive loop"""
    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nSet it with:")
        print('  export ANTHROPIC_API_KEY="your-api-key"  # Linux/Mac')
        print('  $env:ANTHROPIC_API_KEY="your-api-key"  # PowerShell')
        sys.exit(1)
    
    print("="*70)
    print("🎨 AI-Powered Blender Chat")
    print("="*70)
    print("\nInitializing...")
    
    agent = BlenderChatAgent()
    
    try:
        await agent.initialize_mcp()
        
        print("Ready! Start chatting to build your 3D scene.")
        print("Examples:")
        print("  - Create a sphere at the origin")
        print("  - Add a camera looking at the center")
        print("  - Make a scene with 3 cubes")
        print("  - Download a chair model from PolyHaven")
        print("\nType 'quit' to exit\n")
        print("="*70 + "\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\nGoodbye! 👋")
                    break
                
                print()  # Blank line before response
                await agent.chat(user_input)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except EOFError:
                break
    
    finally:
        await agent.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
