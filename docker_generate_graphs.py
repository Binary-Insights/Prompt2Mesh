"""
Generate PNG workflow diagrams for both LangGraph agents
Run this inside the Docker container where the agents are available
"""
import os
import sys
import asyncio
from pathlib import Path

# Add src to Python path
sys.path.insert(0, "/app/src")

# Import agents
from refinement_agent.prompt_refinement_agent import PromptRefinementAgent
from artisan_agent.artisan_agent import ArtisanAgent

async def generate_graphs():
    """Generate PNG diagrams for both workflow graphs"""
    
    # Create output directory
    output_dir = Path("/app/data/graph-workflow")
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
        import traceback
        traceback.print_exc()
    
    # Generate Artisan Agent graph
    try:
        print("2️⃣ Generating Artisan Agent workflow (with refinement loop)...")
        
        # Initialize ArtisanAgent and build graph
        artisan_agent = ArtisanAgent()
        await artisan_agent.initialize()
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
        import traceback
        traceback.print_exc()
    
    print("🎉 Workflow diagram generation complete!")
    print(f"📁 Output directory: {output_dir}")
    
    # List generated files
    print("\n📋 Generated files:")
    for file in output_dir.glob("*.png"):
        print(f"   - {file.name} ({file.stat().st_size:,} bytes)")

if __name__ == "__main__":
    asyncio.run(generate_graphs())
