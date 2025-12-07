# Sculptor Agent - Image-to-3D Modeling

The Sculptor Agent is an AI-powered system that converts 2D images into 3D models in Blender using vision-based analysis and dynamic planning.

## Overview

Unlike the Artisan Agent which works from text prompts, the Sculptor Agent:
- Analyzes 2D input images using Claude Vision
- Dynamically generates modeling steps based on image content
- Iteratively builds 3D models by comparing screenshots with the input
- Automatically refines the model until quality thresholds are met

## Features

✅ **Vision-Based Planning**: AI analyzes your image and creates a custom modeling plan  
✅ **Dynamic Step Generation**: Steps are created on-the-fly based on image complexity  
✅ **Iterative Refinement**: Compares Blender screenshots with input image and improves  
✅ **Resume Mode**: Continue from previous work on the same image  
✅ **Real-time Feedback**: Visual quality scores and progress tracking  
✅ **Blender 4.x/5.x Compatible**: Uses compatibility helpers for cross-version support

## Architecture

### LangGraph Workflow

The Sculptor Agent uses LangGraph with the following nodes:

```
analyze_input_image → load_reference_image → plan_steps → execute_step → 
capture_feedback → assess_progress → [replan/continue/complete]
```

#### Node Descriptions

1. **analyze_input_image**: Uses Claude Vision to analyze the 2D input image
2. **load_reference_image**: Loads the image as a camera background in Blender
3. **plan_steps**: Dynamically generates modeling steps based on vision analysis
4. **execute_step**: Executes current step using Blender Python code
5. **capture_feedback**: Takes viewport screenshot and compares with input
6. **assess_progress**: Evaluates quality and decides next action

### Adaptive Planning

The agent can **replan** during execution:
- Initial plan: 8 steps based on vision analysis
- If quality is low after completing all steps, generates 5 refinement steps
- Maximum 2 replanning attempts to prevent infinite loops

## Usage

### CLI (Command Line)

```bash
# Basic usage
python src/sculptor_agent/run_sculptor.py --input-image path/to/image.png

# With custom session ID
python src/sculptor_agent/run_sculptor.py -i image.jpg --session-id my-session

# Disable resume (fresh start)
python src/sculptor_agent/run_sculptor.py -i image.png --no-resume

# Verbose logging
python src/sculptor_agent/run_sculptor.py -i image.png --verbose
```

### Streamlit Web UI

1. Start the backend server:
```bash
python src/backend/backend_server.py
```

2. Start Streamlit:
```bash
streamlit run src/frontend/app.py
```

3. Navigate to **Sculptor Agent** page
4. Upload a 2D image
5. Click **Start Sculpting**

### Python API

```python
import asyncio
from src.sculptor_agent import SculptorAgent

async def main():
    agent = SculptorAgent(session_id="my-session")
    await agent.initialize()
    
    results = await agent.run(
        image_path="path/to/image.png",
        use_deterministic_session=True
    )
    
    print(f"Success: {results['success']}")
    print(f"Steps: {results['steps_executed']}")
    print(f"Quality scores: {results['quality_scores']}")
    
    await agent.cleanup()

asyncio.run(main())
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Vision Model (for image analysis)
CLAUDE_VISION_MODEL=claude-sonnet-4-20250514

# Reasoning Model (for planning and code generation)
CLAUDE_MODEL=claude-sonnet-4-5-20250929

# Rate Limit Configuration
RATE_LIMIT_MAX_RETRIES=5
RATE_LIMIT_BASE_WAIT=15
RATE_LIMIT_STEP_DELAY=2.0

# LangGraph Configuration
LANGGRAPH_RECURSION_LIMIT=100
```

### Session Resume

By default, sessions are **deterministic** based on image path:
- Same image = same session ID
- Allows resuming interrupted tasks
- To disable: use `--no-resume` or `use_deterministic_session=False`

## Input Image Guidelines

For best results, use images that:

✅ Have clear, well-defined shapes and forms  
✅ Are well-lit with good contrast  
✅ Show front or 3/4 view (easier to model)  
✅ Are simple to medium complexity  
✅ Have distinct objects/elements  

❌ Avoid:
- Very complex scenes with many objects
- Blurry or low-quality images
- Extreme perspectives or angles
- Abstract or unclear subjects

## Output

The Sculptor Agent produces:

1. **3D Model**: Created directly in Blender scene
2. **Screenshots**: Saved to `data/sculptor_screenshots/{session_id}/`
3. **Quality Scores**: Step-by-step quality progression
4. **Vision Analysis**: Detailed analysis of input image
5. **Logs**: Execution logs in `data/logs/`

## Quality Assessment

The agent uses Claude Vision to compare screenshots with the input image:

- **Score**: 0-100% match quality
- **Threshold**: 75% for completion
- **Replanning**: Triggered if final score < 75%

Quality factors:
- Shape accuracy
- Position/layout correctness
- Missing elements
- Incorrect elements

## Troubleshooting

### Agent Not Finding Image

Ensure image path is absolute or relative to project root:
```bash
# Absolute path
python run_sculptor.py -i C:/Users/me/images/test.png

# Relative to project root
python run_sculptor.py -i data/sculptor_images/test.png
```

### Vision Analysis Fails

Check:
- Image file is not corrupted
- Image format is supported (PNG, JPG, BMP, etc.)
- `ANTHROPIC_API_KEY` is set in `.env`
- Rate limits not exceeded

### Low Quality Results

Try:
- Use clearer, higher-quality input images
- Simplify the subject matter
- Use front-facing views
- Manually adjust recursion limit for more steps

### Blender Connection Error

Ensure:
- Blender MCP server is running (`main.py`)
- Blender is listening on correct port
- No firewall blocking connections

## API Endpoints

### POST /sculptor/model
Start a sculptor modeling task

**Request:**
```json
{
  "image_path": "path/to/image.png",
  "use_resume": true
}
```

**Response:**
```json
{
  "task_id": "abc123...",
  "status": "initializing",
  "message": "Sculptor task started"
}
```

### GET /sculptor/status/{task_id}
Get task status and results

**Response:**
```json
{
  "task_id": "abc123...",
  "status": "completed",
  "success": true,
  "steps_executed": 10,
  "screenshots_captured": 10,
  "vision_analysis": "The image shows...",
  "quality_scores": [
    {"step": 1, "score": 40},
    {"step": 2, "score": 55},
    ...
  ],
  "messages": ["Analyzing image...", "Planning steps..."]
}
```

### GET /sculptor/tasks
List all sculptor tasks

### POST /sculptor/cancel/{task_id}
Cancel a running task

## Comparison with Artisan Agent

| Feature | Artisan Agent | Sculptor Agent |
|---------|---------------|----------------|
| Input | Text prompts (JSON) | 2D images |
| Planning | Static from prompt | Dynamic from vision |
| Feedback | Screenshot quality | Image comparison |
| Use Case | Prompt-to-3D | Image-to-3D |
| Refinement | Optional | Built-in with replanning |

## Examples

### Example 1: Simple Cube Drawing

```bash
# Input: Simple cube sketch
python run_sculptor.py -i examples/cube.png
```

Expected steps:
1. Clear scene
2. Add cube primitive
3. Scale and position
4. Add materials
5. Adjust lighting

### Example 2: Character Sketch

```bash
# Input: Character front view
python run_sculptor.py -i examples/character.png
```

Expected steps:
1. Analyze body proportions
2. Add base shapes (head, torso, limbs)
3. Position and scale parts
4. Add modifiers (subdivision, smooth)
5. Basic materials
6. Refinement passes

## Limitations

Current limitations:
- Best for simple to medium complexity objects
- Struggles with very detailed scenes
- Requires clear, unambiguous images
- May need multiple refinement passes
- Limited by Claude Vision token limits

## Future Enhancements

Planned improvements:
- Multi-view support (front, side, top)
- Texture extraction from images
- Better material inference
- Advanced modifier support
- Mesh optimization
- UV unwrapping guidance

## License

Same as main Prompt2Mesh project.

## Support

For issues, questions, or contributions:
- Create an issue on GitHub
- Check logs in `data/logs/`
- Review screenshots in `data/sculptor_screenshots/`
