"""
Generate PNG workflow diagrams for both LangGraph agents
Uses the actual graph objects to create visual diagrams
"""
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from prompt_refinement_agent.prompt_refinement_agent import PromptRefinementAgent
from artisan_agent.artisan_agent import ArtisanAgent

def generate_graphs():
    """Generate PNG diagrams for both workflow graphs"""
    
    # Create output directory
    output_dir = Path(__file__).parent / "data" / "graph-workflow"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎨 Generating workflow diagram PNGs...\n")
    
    # Generate Prompt Refinement Agent graph
    try:
        print("1️⃣ Generating Prompt Refinement Agent workflow...")
        prompt_agent = PromptRefinementAgent()
        prompt_graph = prompt_agent.graph
        
        # Generate PNG
        png_data = prompt_graph.get_graph().draw_mermaid_png()
        
        # Save to file
        prompt_output = output_dir / "prompt_refinement_workflow.png"
        with open(prompt_output, "wb") as f:
            f.write(png_data)
        
        print(f"   ✅ Saved: {prompt_output}")
        print(f"   📏 Size: {len(png_data):,} bytes\n")
        
    except Exception as e:
        print(f"   ❌ Error generating Prompt Refinement graph: {e}\n")
    
    # Generate Artisan Agent graph
    try:
        print("2️⃣ Generating Artisan Agent workflow (with refinement loop)...")
        
        # Note: ArtisanAgent requires MCP client, so we'll import and use minimal initialization
        # We'll need to pass a mock or minimal MCP client
        from unittest.mock import MagicMock
        
        # Create mock MCP client
        mock_mcp = MagicMock()
        mock_mcp.tools = {}
        
        artisan_agent = ArtisanAgent(mcp_client=mock_mcp)
        artisan_graph = artisan_agent.graph
        
        # Generate PNG
        png_data = artisan_graph.get_graph().draw_mermaid_png()
        
        # Save to file
        artisan_output = output_dir / "artisan_agent_workflow.png"
        with open(artisan_output, "wb") as f:
            f.write(png_data)
        
        print(f"   ✅ Saved: {artisan_output}")
        print(f"   📏 Size: {len(png_data):,} bytes\n")
        
    except Exception as e:
        print(f"   ❌ Error generating Artisan Agent graph: {e}\n")
    
    print("🎉 Workflow diagram generation complete!")
    print(f"📁 Output directory: {output_dir}")

if __name__ == "__main__":
    generate_graphs()
