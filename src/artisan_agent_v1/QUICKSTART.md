# Artisan Agent - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Prerequisites

1. **Blender** running with MCP addon
2. **Python 3.11+** installed
3. **Dependencies** installed:
   ```bash
   pip install langchain langchain-anthropic langgraph langsmith anthropic mcp streamlit python-dotenv
   ```

4. **Environment variables** configured in `.env`:
   ```env
   ANTHROPIC_API_KEY=your_key_here
   LANGCHAIN_API_KEY=your_langsmith_key
   LANGCHAIN_TRACING_V2=true
   ```

### Step 1: Create a Requirement File

Use the Prompt Refinement Agent to create a detailed requirement:

```bash
# Start backend
uvicorn src.backend.backend_server:app --reload

# Start frontend (in another terminal)
streamlit run src/frontend/streamlit_blender_chat_with_refinement.py
```

Or use the existing example:
```
data/prompts/json/20251127_135557_Could_you_model_a_ch.json
```

### Step 2: Run Artisan Agent

**Option A: Command Line (Recommended for first test)**

```bash
python src/artisan_agent/run_artisan.py \
  --input-file data/prompts/json/20251127_135557_Could_you_model_a_ch.json \
  --verbose
```

**Option B: Streamlit Interface**

```bash
streamlit run src/artisan_agent/streamlit_artisan.py
```

### Step 3: Watch the Magic!

The agent will:
1. ✅ Connect to Blender (you'll see connection in Blender console)
2. 📋 Create a step-by-step plan
3. 🔧 Execute each step sequentially
4. 📸 Take screenshots after major operations
5. ✅ Complete and save results

### Step 4: Review Results

**Screenshots are saved to:**
```
data/blender/screenshots/{session_id}/
```

**Check Blender** - Your 3D model should be created!

**View results:**
- Screenshots: `data/blender/screenshots/{session_id}/`
- Log file: `data/logs/artisan_agent_YYYYMMDD_HHMMSS_<session_id>.log`
- LangSmith traces: https://smith.langchain.com

**Verbose mode for debugging:**
```bash
python src/artisan_agent/run_artisan.py -i your_file.json --verbose
```

## 🎯 Example Run

```bash
$ python src/artisan_agent/run_artisan.py -i data/prompts/json/20251127_135557_Could_you_model_a_ch.json

================================================================================
🎨 ARTISAN AGENT - Autonomous 3D Modeling
================================================================================

📄 Input File: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
🔑 Session ID: bf37c46d-920f-48cc-9fe8-2e22f8105a51
📝 Log File: data/logs/artisan_agent_20251127_180314_bf37c46d.log

--------------------------------------------------------------------------------

ℹ️ Initializing Artisan Agent...
✅ Connected to Blender with 15 tools
✅ Agent workflow initialized

--------------------------------------------------------------------------------

ℹ️ Starting modeling workflow...
📋 Planning modeling steps...
✅ Created 12-step plan
  1. Clear the default scene and set up units
  2. Create the main trunk cylinder
  3. Create the bottom tier of branches
  ...

🔧 Step 1/12: Clear the default scene and set up units
  🔧 Calling: execute_blender_code
  ✅ execute_blender_code completed

📸 Capturing viewport screenshot...
✅ Screenshot saved: step_1_screenshot_0.png

🤔 Evaluating progress...
ℹ️ 11 steps remaining

...

✅ All steps completed!

================================================================================
📊 MODELING RESULTS
================================================================================

✅ Success: True
📋 Steps Executed: 12
📸 Screenshots Captured: 8
📁 Screenshot Directory: data/blender/screenshots/20251127_143022
🔑 Session ID: 20251127_143022

================================================================================

🧹 Cleanup complete
```

## 🐛 Troubleshooting

### "Connection refused"
**Problem**: Can't connect to Blender MCP
**Solution**: 
1. Make sure Blender is running
2. Enable the MCP addon
3. Click "Start Server" in BlenderMCP panel

### "No 'refined_prompt' found"
**Problem**: Invalid JSON file
**Solution**: Use files from `data/prompts/json/` created by Prompt Refinement Agent

### "Tool execution failed"
**Problem**: Blender code error
**Solution**: Check Blender's console for Python errors

### Import errors
**Problem**: Missing dependencies
**Solution**: 
```bash
pip install langchain langchain-anthropic langgraph langsmith anthropic mcp streamlit
```

## 💡 Tips

1. **Use verbose mode** (`-v`) to see detailed tool execution
2. **Custom session IDs** help organize screenshots: `--session-id my-project-v1`
3. **Check LangSmith** for debugging - all operations are traced
4. **Start simple** - test with the example Christmas tree JSON first
5. **Monitor Blender** - watch the viewport as the agent works

## 📚 Next Steps

- Read [README.md](README.md) for detailed documentation
- Check [IMPLEMENTATION.md](IMPLEMENTATION.md) for technical details
- Review [LangSmith traces](https://smith.langchain.com) to understand agent reasoning
- Experiment with different requirements
- Integrate into your workflow

## 🎉 You're Ready!

Start creating autonomous 3D models with:
```bash
python src/artisan_agent/run_artisan.py -i path/to/your/requirement.json
```

Happy modeling! 🎨
