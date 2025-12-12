#!/usr/bin/env python3
"""
Interactive MCP Client for Blender
Allows calling MCP tools from the command line
"""
import sys
import json
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def run_mcp_tool(tool_name: str, arguments: dict = None):
    """Run an MCP tool and return the result"""
    server_params = StdioServerParameters(
        command="python",
        args=["main.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools = await session.list_tools()
            print(f"\n📋 Available tools: {[t.name for t in tools.tools]}\n")
            
            # Call the requested tool
            if tool_name:
                print(f"🔧 Calling tool: {tool_name}")
                if arguments:
                    print(f"📝 Arguments: {json.dumps(arguments, indent=2)}")
                
                result = await session.call_tool(tool_name, arguments or {})
                print(f"\n✅ Result:\n{json.dumps(result.content, indent=2)}\n")
                return result
            
            return tools

async def interactive_mode():
    """Run in interactive mode"""
    print("="*70)
    print("🎨 Blender MCP Interactive Client")
    print("="*70)
    
    server_params = StdioServerParameters(
        command="python",
        args=["main.py"],
        env=None
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # List available tools
            tools_response = await session.list_tools()
            tools = {t.name: t for t in tools_response.tools}
            
            print("\n📋 Available MCP Tools:")
            for i, tool_name in enumerate(sorted(tools.keys()), 1):
                tool = tools[tool_name]
                print(f"  {i}. {tool_name}")
                if tool.description:
                    print(f"     {tool.description[:80]}...")
            
            print("\n" + "="*70)
            print("Commands:")
            print("  list - Show all available tools")
            print("  call <tool_name> [json_args] - Call a tool")
            print("  help <tool_name> - Show tool details")
            print("  quit - Exit")
            print("="*70 + "\n")
            
            while True:
                try:
                    command = input("→ ").strip()
                    
                    if not command:
                        continue
                    
                    if command in ['quit', 'exit', 'q']:
                        print("Goodbye!")
                        break
                    
                    parts = command.split(maxsplit=1)
                    cmd = parts[0].lower()
                    
                    if cmd == 'list':
                        print("\n📋 Available tools:")
                        for tool_name in sorted(tools.keys()):
                            print(f"  • {tool_name}")
                        print()
                    
                    elif cmd == 'help':
                        if len(parts) < 2:
                            print("Usage: help <tool_name>")
                            continue
                        
                        tool_name = parts[1]
                        if tool_name not in tools:
                            print(f"❌ Tool '{tool_name}' not found")
                            continue
                        
                        tool = tools[tool_name]
                        print(f"\n🔧 {tool_name}")
                        print(f"Description: {tool.description}")
                        if tool.inputSchema:
                            print(f"Parameters: {json.dumps(tool.inputSchema, indent=2)}")
                        print()
                    
                    elif cmd == 'call':
                        if len(parts) < 2:
                            print("Usage: call <tool_name> [json_args]")
                            continue
                        
                        args_parts = parts[1].split(maxsplit=1)
                        tool_name = args_parts[0]
                        
                        if tool_name not in tools:
                            print(f"❌ Tool '{tool_name}' not found")
                            continue
                        
                        # Parse arguments if provided
                        arguments = {}
                        if len(args_parts) > 1:
                            try:
                                arguments = json.loads(args_parts[1])
                            except json.JSONDecodeError as e:
                                print(f"❌ Invalid JSON arguments: {e}")
                                continue
                        
                        print(f"\n🔧 Calling {tool_name}...")
                        try:
                            result = await session.call_tool(tool_name, arguments)
                            print(f"\n✅ Result:")
                            for content in result.content:
                                if hasattr(content, 'text'):
                                    print(content.text)
                                else:
                                    print(content)
                            print()
                        except Exception as e:
                            print(f"❌ Error: {e}\n")
                    
                    else:
                        print(f"Unknown command: {cmd}")
                        print("Try: list, call, help, or quit")
                
                except KeyboardInterrupt:
                    print("\n\nInterrupted by user")
                    break
                except EOFError:
                    break

def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        # Command mode: call a specific tool
        tool_name = sys.argv[1]
        arguments = {}
        
        if len(sys.argv) > 2:
            try:
                arguments = json.loads(sys.argv[2])
            except json.JSONDecodeError:
                print(f"Error: Invalid JSON arguments: {sys.argv[2]}")
                sys.exit(1)
        
        asyncio.run(run_mcp_tool(tool_name, arguments))
    else:
        # Interactive mode
        asyncio.run(interactive_mode())

if __name__ == "__main__":
    main()
