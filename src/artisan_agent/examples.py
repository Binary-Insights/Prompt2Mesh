"""
Example: Using Artisan Agent Programmatically
Demonstrates how to integrate the agent into your own code
"""
import asyncio
import json
from pathlib import Path
from src.artisan_agent import ArtisanAgent


# Example 1: Basic Usage
async def basic_example():
    """Simple example of running the agent"""
    print("=" * 60)
    print("Example 1: Basic Usage")
    print("=" * 60)
    
    # Create agent
    agent = ArtisanAgent()
    
    try:
        # Initialize
        await agent.initialize()
        
        # Run with JSON file
        results = await agent.run(
            "data/prompts/json/20251127_135557_Could_you_model_a_ch.json"
        )
        
        # Access results
        print(f"\n✅ Modeling complete!")
        print(f"Session ID: {results['session_id']}")
        print(f"Steps: {results['steps_executed']}")
        print(f"Screenshots: {results['screenshots_captured']}")
        
    finally:
        await agent.cleanup()


# Example 2: Custom Session ID
async def custom_session_example():
    """Example with custom session ID for organization"""
    print("\n" + "=" * 60)
    print("Example 2: Custom Session ID")
    print("=" * 60)
    
    # Use meaningful session ID
    agent = ArtisanAgent(session_id="christmas-tree-v2")
    
    try:
        await agent.initialize()
        results = await agent.run(
            "data/prompts/json/20251127_135557_Could_you_model_a_ch.json"
        )
        
        print(f"\n✅ Screenshots saved to: {results['screenshot_directory']}")
        
    finally:
        await agent.cleanup()


# Example 3: Custom Display Callback
async def custom_display_example():
    """Example with custom progress display"""
    print("\n" + "=" * 60)
    print("Example 3: Custom Display Callback")
    print("=" * 60)
    
    # Define custom callback
    def my_display(message: str, type: str = "info"):
        """Custom display function"""
        timestamp = __import__('datetime').datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{type.upper()}] {message}")
    
    # Create agent with callback
    agent = ArtisanAgent(
        session_id="custom-display-example",
        display_callback=my_display
    )
    
    try:
        await agent.initialize()
        results = await agent.run(
            "data/prompts/json/20251127_135557_Could_you_model_a_ch.json"
        )
        
        print(f"\n✅ Done! Check {results['screenshot_directory']}")
        
    finally:
        await agent.cleanup()


# Example 4: Processing Multiple Requirements
async def batch_processing_example():
    """Example of processing multiple JSON files"""
    print("\n" + "=" * 60)
    print("Example 4: Batch Processing")
    print("=" * 60)
    
    # Find all JSON files
    json_dir = Path("data/prompts/json")
    json_files = list(json_dir.glob("*.json"))[:3]  # Process first 3
    
    print(f"Processing {len(json_files)} files...")
    
    # Create agent once
    agent = ArtisanAgent()
    
    try:
        await agent.initialize()
        
        all_results = []
        
        for i, json_file in enumerate(json_files, 1):
            print(f"\n📄 File {i}/{len(json_files)}: {json_file.name}")
            
            # Process each file
            results = await agent.run(str(json_file))
            all_results.append(results)
            
            print(f"  ✅ Steps: {results['steps_executed']}")
            print(f"  📸 Screenshots: {results['screenshots_captured']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("Batch Processing Summary")
        print("=" * 60)
        total_steps = sum(r['steps_executed'] for r in all_results)
        total_screenshots = sum(r['screenshots_captured'] for r in all_results)
        print(f"Total files processed: {len(all_results)}")
        print(f"Total steps executed: {total_steps}")
        print(f"Total screenshots: {total_screenshots}")
        
    finally:
        await agent.cleanup()


# Example 5: Error Handling
async def error_handling_example():
    """Example with comprehensive error handling"""
    print("\n" + "=" * 60)
    print("Example 5: Error Handling")
    print("=" * 60)
    
    agent = ArtisanAgent(session_id="error-handling-test")
    
    try:
        await agent.initialize()
        
        # Try to process a file
        json_file = "data/prompts/json/20251127_135557_Could_you_model_a_ch.json"
        
        if not Path(json_file).exists():
            print(f"❌ File not found: {json_file}")
            return
        
        results = await agent.run(json_file)
        
        # Check for success
        if results['success']:
            print(f"✅ Modeling successful!")
            print(f"   Steps: {results['steps_executed']}")
        else:
            print(f"⚠️ Modeling incomplete")
            print(f"   Steps completed: {results['steps_executed']}")
        
        # Analyze tool results
        failed_tools = [
            t for t in results['tool_results'] 
            if not t['success']
        ]
        
        if failed_tools:
            print(f"\n⚠️ {len(failed_tools)} tool(s) failed:")
            for tool in failed_tools:
                print(f"   - {tool['tool_name']}: {tool['result'][:100]}")
        
    except FileNotFoundError as e:
        print(f"❌ File error: {e}")
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.cleanup()


# Example 6: Accessing Tool Results
async def tool_results_example():
    """Example showing how to access detailed tool results"""
    print("\n" + "=" * 60)
    print("Example 6: Accessing Tool Results")
    print("=" * 60)
    
    agent = ArtisanAgent()
    
    try:
        await agent.initialize()
        results = await agent.run(
            "data/prompts/json/20251127_135557_Could_you_model_a_ch.json"
        )
        
        print(f"\n📊 Tool Execution Analysis")
        print("-" * 60)
        
        # Group by tool name
        tool_counts = {}
        for tool_result in results['tool_results']:
            tool_name = tool_result['tool_name']
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        print("\nTool usage:")
        for tool_name, count in sorted(tool_counts.items()):
            print(f"  {tool_name}: {count} calls")
        
        # Find screenshots
        screenshot_results = [
            t for t in results['tool_results']
            if t['tool_name'] == 'get_viewport_screenshot'
        ]
        
        print(f"\n📸 Screenshots captured: {len(screenshot_results)}")
        
        # Check for errors
        errors = [
            t for t in results['tool_results']
            if not t['success']
        ]
        
        if errors:
            print(f"\n⚠️ Errors encountered: {len(errors)}")
            for error in errors:
                print(f"  - {error['tool_name']}: {error['result'][:100]}")
        else:
            print("\n✅ No errors!")
        
    finally:
        await agent.cleanup()


# Main function to run all examples
async def main():
    """Run all examples"""
    print("\n🎨 Artisan Agent - Programmatic Usage Examples\n")
    
    # Choose which examples to run
    examples = [
        ("Basic Usage", basic_example),
        ("Custom Session ID", custom_session_example),
        ("Custom Display", custom_display_example),
        # ("Batch Processing", batch_processing_example),  # Uncomment to run
        ("Error Handling", error_handling_example),
        ("Tool Results Analysis", tool_results_example),
    ]
    
    for i, (name, example_func) in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Running Example {i}/{len(examples)}: {name}")
        print(f"{'='*60}")
        
        try:
            await example_func()
        except KeyboardInterrupt:
            print("\n\n⚠️ Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Example failed: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print(f"Example {i} Complete")
        print("="*60)
        
        # Pause between examples
        if i < len(examples):
            await asyncio.sleep(2)
    
    print("\n✅ All examples complete!")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("⚠️  IMPORTANT: Make sure Blender is running with MCP addon!")
    print("="*60)
    input("\nPress Enter to continue...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️ Interrupted by user")
