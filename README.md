# Prompt2Mesh
Final Project - Control Blender with Natural Language

## Quick Start

### 1. Start Blender with the Addon

1. Open **Blender**
2. Install the addon:
   - Edit → Preferences → Add-ons → Install
   - Select `addon.py` from this directory
   - Enable "Blender MCP"
3. Start the server:
   - Press `N` in 3D View to show sidebar
   - Click "BlenderMCP" tab
   - Click "Start Server"

### 2. Test the Connection

Use the interactive client to create a sphere with physics:

```bash
python interactive_client.py
```

Choose option 1 to create a sphere with gravity, then press **SPACEBAR** in Blender to run the physics simulation!

## What This Does

This project bridges AI assistants to Blender using the Model Context Protocol (MCP):

- **Blender Addon** (`addon.py`): Runs inside Blender, listens on port 9876
- **MCP Server** (`main.py`): Translates MCP requests to Blender commands
- **Interactive Client** (`interactive_client.py`): Test tool for direct commands

## Files

- `SETUP_GUIDE.md` - Detailed setup instructions
- `test_blender_connection.py` - Connection test suite
- `interactive_client.py` - Interactive CLI for testing
- `main.py` - MCP server entry point
- `addon.py` - Blender addon
- `src/blender_mcp/server.py` - MCP server implementation

## Usage

### With Interactive Client

```bash
python interactive_client.py
```

Options:
- `1` - Create sphere with gravity physics
- `2` - Create bouncing cubes
- `custom` - Enter custom Python code
- `info` - Get Blender version info

### With MCP Clients (Claude Desktop, Cline, etc.)

See `SETUP_GUIDE.md` for configuration instructions.

## Troubleshooting

**"Connection refused" error:**
- Make sure Blender is running
- The addon must be installed and enabled
- The server must be started in Blender (BlenderMCP panel)

**"Invalid JSON" error:**
- Don't run `main.py` directly and type commands
- Use `interactive_client.py` for testing
- Use an MCP client for production use

See `SETUP_GUIDE.md` for more details.

## 🤖 AI Agents

This project includes advanced AI agents for autonomous 3D modeling:

### Artisan Agent - Autonomous 3D Modeling

An intelligent agent that reads requirements and autonomously builds 3D models in Blender.

**Features:**
- 📖 Reads detailed requirements from JSON files
- 🧠 Plans sequential modeling steps using Claude Sonnet 4.5
- 🔧 Executes Blender MCP tools automatically
- 📸 Captures viewport screenshots for visual feedback
- 🔄 Iterates until modeling is complete
- 📊 Full LangSmith tracing for debugging

**Quick Start:**

```bash
# Command line
python src/artisan_agent/run_artisan.py --input-file data/prompts/json/your_requirement.json

# Web interface
streamlit run src/artisan_agent/streamlit_artisan.py
```

See [Artisan Agent README](src/artisan_agent/README.md) for detailed documentation.

### Prompt Refinement Agent

Expands simple user prompts into detailed 3D modeling specifications.

**Features:**
- Analyzes user intent
- Generates comprehensive technical specifications
- Includes dimensions, materials, textures, and rendering details
- Multiple detail levels (concise/moderate/comprehensive)
- Saves requirements as JSON for Artisan Agent

**Usage:**

```bash
# Backend API
uvicorn src.backend.backend_server:app --reload

# Frontend
streamlit run src/frontend/streamlit_blender_chat_with_refinement.py
```

See [Prompt Refinement README](src/refinement_agent/) for more details.

