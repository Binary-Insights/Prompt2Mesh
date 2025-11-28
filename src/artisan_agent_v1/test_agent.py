"""
Quick Test Script for Artisan Agent
Tests the agent with a sample requirement file
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.artisan_agent import ArtisanAgent


async def test_agent():
    """Test the Artisan Agent with example JSON"""
    
    print("=" * 80)
    print("🧪 ARTISAN AGENT TEST")
    print("=" * 80)
    
    # Find test JSON file
    test_file = Path("data/prompts/json/20251127_135557_Could_you_model_a_ch.json")
    
    if not test_file.exists():
        print(f"\n❌ Test file not found: {test_file}")
        print("\nPlease ensure the example JSON file exists or specify a different file.")
        return
    
    print(f"\n📄 Using test file: {test_file}")
    print("\n" + "-" * 80 + "\n")
    
    # Create agent
    agent = ArtisanAgent(session_id="test-session")
    
    try:
        # Initialize
        print("🔧 Initializing agent...")
        await agent.initialize()
        
        print("\n" + "-" * 80 + "\n")
        
        # Run modeling task
        print("🚀 Starting modeling task...")
        results = await agent.run(str(test_file))
        
        # Display results
        print("\n" + "=" * 80)
        print("✅ TEST COMPLETE")
        print("=" * 80)
        print(f"\nSession ID: {results['session_id']}")
        print(f"Steps Executed: {results['steps_executed']}")
        print(f"Screenshots Captured: {results['screenshots_captured']}")
        print(f"Screenshot Directory: {results['screenshot_directory']}")
        print(f"Success: {results['success']}")
        
        print("\n" + "=" * 80 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        await agent.cleanup()
        print("🧹 Cleanup complete")


if __name__ == "__main__":
    print("\nℹ️  Make sure Blender is running with MCP addon enabled!")
    print("ℹ️  Press Ctrl+C to cancel\n")
    
    try:
        asyncio.run(test_agent())
    except KeyboardInterrupt:
        print("\n\n⚠️ Test interrupted by user")
        sys.exit(130)
