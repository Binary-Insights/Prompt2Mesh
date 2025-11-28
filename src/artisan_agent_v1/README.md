# Artisan Agent - Autonomous 3D Modeling Agent

An intelligent agent that autonomously creates 3D models in Blender by reading requirements, planning steps, executing tools, and iterating with visual feedback.

## 🎯 Overview

Artisan Agent is a LangGraph-powered autonomous agent that:

- 📖 **Reads** detailed modeling requirements from JSON files
- 🧠 **Plans** sequential steps using Claude Sonnet 4.5
- 🔧 **Executes** Blender MCP tools to build the model
- 📸 **Captures** viewport screenshots for visual feedback
- 🔄 **Iterates** until the modeling task is complete
- 📊 **Traces** all operations using LangSmith

## 🏗️ Architecture

### LangGraph Workflow

```
┌─────────┐
│  Plan   │ - Analyze requirement and create step-by-step plan
└────┬────┘
     │
     ▼
┌─────────────┐
│Execute Step │ - Execute current modeling step with Blender tools
└─────┬───────┘
      │
      ▼
┌──────────────┐
│Capture       │ - Take viewport screenshot for feedback
│Feedback      │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Evaluate    │ - Check if modeling is complete
│  Progress    │
└──────┬───────┘
       │
       ├─── Not Complete ──> Execute Step
       │
       └─── Complete ──────> End
```

### Components

1. **ArtisanAgent** (`artisan_agent.py`)
   - Core agent with LangGraph workflow
   - State management and execution logic
   - Screenshot capture and storage

2. **BlenderMCPConnection** (in `artisan_agent.py`)
   - MCP client for Blender communication
   - Tool execution and result handling
   - Image data processing

3. **CLI Interface** (`run_artisan.py`)
   - Standalone command-line script
   - Argument parsing and execution
   - Console output display

4. **Streamlit Interface** (`streamlit_artisan.py`)
   - Web-based UI
   - Real-time progress display
   - Screenshot gallery

## 📦 Installation

Ensure you have the required dependencies:

```bash
pip install langchain langchain-anthropic langgraph langsmith anthropic mcp streamlit python-dotenv
```

## 🚀 Usage

### Option 1: Command Line (Standalone)

```bash
# Basic usage
python src/artisan_agent/run_artisan.py --input-file data/prompts/json/20251127_135557_Could_you_model_a_ch.json

# With custom session ID
python src/artisan_agent/run_artisan.py -i data/prompts/json/your_file.json -s my-session-123

# Verbose mode (shows detailed tool execution)
python src/artisan_agent/run_artisan.py -i data/prompts/json/your_file.json -v
```

**Arguments:**
- `--input-file, -i` (required): Path to JSON requirement file
- `--session-id, -s` (optional): Custom session ID (auto-generated if not provided)
- `--verbose, -v` (optional): Enable verbose output

### Option 2: Streamlit Web UI

```bash
streamlit run src/artisan_agent/streamlit_artisan.py
```

Then:
1. Select a requirement JSON file from the sidebar
2. Review the requirement preview
3. Click "Start Modeling"
4. Watch real-time progress
5. View screenshots and results

## 📄 Input Format

The agent reads JSON files from `data/prompts/json/` with this structure:

```json
{
  "refined_prompt": "Detailed 3D modeling description with measurements, materials, etc.",
  "original_prompt": "Simple user request",
  "timestamp": "2025-11-27 13:55:57",
  "is_detailed": false
}
```

**Key field:** `refined_prompt` - This is the detailed requirement the agent follows.

You can generate these files using the **Prompt Refinement Agent**.

## 📝 Logging

All agent operations are automatically logged to:
```
data/logs/artisan_agent_YYYYMMDD_HHMMSS_<session_id>.log
```

**Log contents:**
- Agent initialization and configuration
- Planning steps and decisions
- Tool execution results
- Screenshot capture events
- Errors and warnings
- Session summary

**Log levels:**
- `--verbose` flag: DEBUG level (detailed tool arguments, full tracebacks)
- Normal mode: INFO level (major events, progress updates)

**Example log file:**
```
data/logs/artisan_agent_20251127_180314_bf37c46d.log
```

Logs are useful for:
- Debugging issues
- Understanding agent decision-making
- Audit trail of all operations
- Performance analysis

## 📸 Screenshot Storage

Screenshots are automatically saved to:
```
data/blender/screenshots/{session_id}/
  ├── step_1_screenshot_0.png
  ├── step_2_screenshot_1.png
  └── ...
```

Each screenshot captures the viewport state after significant modeling steps.

## 🔍 LangSmith Tracing

All functions are decorated with `@traceable` for LangSmith monitoring:

- `initialize_artisan_agent` - Agent initialization
- `plan_modeling_steps` - Planning phase
- `execute_modeling_step` - Step execution
- `capture_viewport_feedback` - Screenshot capture
- `evaluate_modeling_progress` - Progress evaluation
- `run_modeling_task` - Full workflow
- `initialize_blender_mcp` - MCP connection
- `call_blender_tool` - Tool calls

View traces at: https://smith.langchain.com

## 🛠️ Available Blender Tools

The agent can use all Blender MCP tools:

- `execute_blender_code` - Execute Python code in Blender
- `get_scene_info` - Get current scene information
- `get_viewport_screenshot` - Capture viewport screenshot
- `get_object_info` - Get specific object details
- Plus integration tools for PolyHaven, Hyper3D, Sketchfab

## 📊 Output

The agent returns a results dictionary:

```python
{
  "session_id": "abc123",
  "requirement": "Full refined prompt text...",
  "steps_executed": 12,
  "screenshots_captured": 8,
  "screenshot_directory": "data/blender/screenshots/abc123",
  "success": True,
  "tool_results": [...]
}
```

## 🔧 Configuration

Environment variables (in `.env`):

```env
ANTHROPIC_API_KEY=your_api_key
CLAUDE_MODEL=claude-sonnet-4-5-20250929
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ReAct-LangGraph-Function-Call
LANGCHAIN_CALLBACKS_BACKGROUND=true
```

## 🎯 Example Workflow

1. **User creates requirement:**
   ```bash
   # Use refinement agent to create detailed requirement
   # Result: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
   ```

2. **Run Artisan Agent:**
   ```bash
   python src/artisan_agent/run_artisan.py -i data/prompts/json/20251127_135557_Could_you_model_a_ch.json
   ```

3. **Agent workflow:**
   - Connects to Blender MCP
   - Analyzes requirement (Christmas tree)
   - Creates 12-step plan
   - Executes each step sequentially
   - Captures screenshots after each major operation
   - Iterates until complete

4. **Review results:**
   - Check console output for progress
   - View screenshots in `data/blender/screenshots/{session_id}/`
   - Check LangSmith for detailed traces

## 🐛 Troubleshooting

For comprehensive troubleshooting, see **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)**

**Quick Fixes:**

**"No 'refined_prompt' found in JSON file"**
- Ensure JSON file has `refined_prompt` key
- Use Prompt Refinement Agent to create valid files

**"Connection to Blender failed"**
- Ensure Blender is running with MCP addon
- Check that `main.py` is in the project root
- Verify MCP server is configured correctly

**"RuntimeError during cleanup"** ✅ FIXED
- Update to latest code - cleanup errors are now suppressed
- This error is cosmetic and doesn't affect functionality

**"Tool execution failed"**
- Check Blender console for Python errors
- Ensure objects/materials exist before referencing
- Try breaking complex operations into smaller steps

## 📚 Additional Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - 5-minute quick start guide
- **[IMPLEMENTATION.md](IMPLEMENTATION.md)** - Technical implementation details
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[LOGGING.md](LOGGING.md)** - Logging system documentation with examples
- **[examples.py](examples.py)** - Programmatic usage examples

## 📝 Notes

- The agent uses **Claude Sonnet 4.5** for planning and decision-making
- Screenshots are captured at **800px max dimension** by default
- Session IDs use timestamp format: `YYYYMMDD_HHMMSS`
- All operations are traced in LangSmith for debugging

## 🔗 Related Components

- **Prompt Refinement Agent** (`src/refinement_agent/`) - Creates detailed requirements
- **Blender Chat Agent** (`src/blender/blender_agent.py`) - Interactive Blender control
- **Blender MCP Server** (`src/blender_mcp/server.py`) - MCP server implementation
- **Backend API** (`src/backend/backend_server.py`) - FastAPI backend

## 📄 License

Same as parent project (Prompt2Mesh)
