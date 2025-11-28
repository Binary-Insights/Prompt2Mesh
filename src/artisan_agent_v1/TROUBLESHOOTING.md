# Troubleshooting Guide

## Common Issues and Solutions

### RuntimeError during cleanup (FIXED)

**Symptom:**
```
RuntimeError: Attempted to exit cancel scope in a different task than it was entered in
```

**Cause:**
This error occurs when the `stdio_client` async context manager from the MCP library attempts to clean up in a different asyncio task context than where it was created. This is a common issue with async generators and context managers in asyncio.

**Solution:**
The error has been fixed with improved exception handling:

1. **Wrapped cleanup calls in try-except blocks** - All cleanup operations now suppress `RuntimeError`, `GeneratorExit`, and `BaseExceptionGroup` exceptions
2. **Added cleanup delay** - Added a small 0.1s delay after cleanup to allow async tasks to finish gracefully
3. **Prevent double cleanup** - Added `_cleanup_done` flag to prevent cleanup being called multiple times

**Code Changes:**
- `artisan_agent.py`: Enhanced `BlenderMCPConnection.cleanup()` to catch and suppress cleanup errors
- `run_artisan.py`: Added try-except wrapper around `agent.cleanup()` and post-cleanup delay
- `streamlit_artisan.py`: Added try-except wrapper around `agent.cleanup()`

**Impact:**
- The agent still completes successfully
- Screenshots are still captured
- Model is still created
- Only the cleanup error message is suppressed

### Tool Use Without Tool Result Error (FIXED v1.1.2)

**Symptom:**
```
anthropic.BadRequestError: Error code: 400 - 'tool_use' ids were found without 'tool_result' blocks
```

**Cause:**
The Anthropic API requires every `tool_use` block to be followed by a `tool_result` block. The agent was executing tools but not adding the result messages to the conversation history in the correct format.

**Solution (v1.1.2+):**
Fixed in version 1.1.2 - the agent now properly creates `ToolMessage` objects after each tool execution:
- Each tool result is wrapped in a ToolMessage
- ToolMessage includes the tool_call_id to match the tool_use
- Messages are added in correct order: AI response, then ToolMessages
- Allows multi-step workflows to execute successfully

**Status:** ✅ FIXED - Update to v1.1.2 or later

### Recursion Limit Exceeded (FIXED v1.1.2)

**Symptom:**
```
langgraph.errors.GraphRecursionError: Recursion limit of 25 reached without hitting a stop condition
```

**Cause:**
LangGraph has a default recursion limit of 25 iterations to prevent infinite loops. With a 12-step modeling plan, the workflow requires more iterations:
- Each step goes through: execute → capture_feedback → evaluate_progress → (loop back)
- 12 steps × 3-4 nodes per step = 36-48 iterations
- Default limit of 25 was too low

**Solution (v1.1.2+):**
Fixed in version 1.1.2 - recursion limit increased to 100:
```python
config = {
    "configurable": {"thread_id": session_id},
    "recursion_limit": 100  # Allows up to 100 graph iterations
}
```

**Custom Adjustment:**
If you need even more steps, edit `artisan_agent.py` line ~530:
```python
"recursion_limit": 200  # For 50+ step plans
```

**Status:** ✅ FIXED - Update to v1.1.2 or later

### Connection Reset by Peer

**Symptom:**
```
Socket connection error: [Errno 104] Connection reset by peer
```

**Cause:**
The Blender MCP server connection was lost, typically because:
- Blender crashed or was closed
- The addon was reloaded
- Network timeout

**Solution:**
The code automatically reconnects when this happens. No user action required.

### No Planning Steps Created

**Symptom:**
```
✅ Created 0-step plan
Steps Executed: 0
```

**Cause:**
The LLM's planning response failed to parse into actionable steps. This can happen if:
- The response format doesn't match the expected numbered list
- The requirement is too vague or complex
- The LLM response parsing regex failed

**Solution (v1.1.1+):**
The system now includes:
1. **Improved parsing** - Multiple patterns recognized (1., 1), Step 1:, etc.)
2. **Fallback plan** - If parsing fails, uses a 5-step generic template
3. **Detailed logging** - Shows exactly what the LLM returned and what was parsed

**Debug with verbose mode:**
```bash
python src/artisan_agent/run_artisan.py -i your_file.json --verbose
```

Check the log file for:
```log
INFO - LLM response length: XXX characters
DEBUG - LLM response: [shows first 500 chars]
INFO - Parsed X steps from LLM response
```

If you see "Parsed 0 steps", check the DEBUG log to see the LLM response format.

**Fallback behavior:**
If no steps are parsed, the system automatically uses these generic steps:
1. Clear default scene and set up environment
2. Create main geometry based on requirements
3. Add details and refinements
4. Apply materials and lighting
5. Final adjustments and capture screenshot

**Expected Behavior:**
With proper requirements, you should see 5-15 steps created.

### Screenshots Not Appearing

**Check:**
1. Screenshot directory exists: `data/blender/screenshots/{session_id}/`
2. Blender viewport is visible and not minimized
3. The screenshot tool completed successfully (check logs)

**Solution:**
- Make sure Blender window is visible
- Check `data/blender/screenshots/` for the session ID folder
- Look for `step_N_screenshot_M.png` files

### LangSmith Tracing Not Working

**Check:**
1. `.env` file contains:
   ```
   LANGCHAIN_TRACING_V2=true
   LANGCHAIN_API_KEY=your_key_here
   LANGCHAIN_PROJECT=ReAct-LangGraph-Function-Call
   ```

2. Environment variables are loaded:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

**Solution:**
- Verify API key is valid
- Check network connectivity
- Traces appear at: https://smith.langchain.com/

### Agent Runs But Creates Nothing

**Possible Causes:**
1. **Empty requirement** - Check JSON file has `refined_prompt` key
2. **Blender not connected** - Verify addon is loaded and listening on port 9876
3. **Tools not available** - Check that 17 tools are reported on startup

**Debug Steps:**
1. Run with `--verbose` flag to see detailed tool execution
2. Check Blender console for errors
3. Verify MCP connection: `python test_blender_connection.py`
4. Review LangSmith traces for tool call details

## Best Practices

### Avoid Rate Limits
- Use shorter, more focused requirements
- Use "concise" detail level in refinement
- Break complex models into multiple sessions

### Optimize Screenshot Capture
- Only capture when needed for feedback
- Screenshots are saved automatically after each major step
- Review screenshots to understand agent's progress

### Session Management
- Each run creates unique session ID
- Screenshots organized by session
- Use custom session ID for specific tracking:
  ```bash
  python src/artisan_agent/run_artisan.py \
    --input-file data/prompts/json/your_file.json \
    --session-id my-custom-session
  ```

### Debugging Workflow
1. **Enable verbose mode**: `--verbose` flag
2. **Check LangSmith**: Review traces at smith.langchain.com
3. **Examine screenshots**: Visual feedback in session folder
4. **Review logs**: Console output shows each step
5. **Validate JSON**: Ensure refined_prompt exists in input file

## Getting Help

### Logs to Collect
When reporting issues, include:
- Full console output (with `--verbose` if possible)
- Input JSON file
- Session ID
- Screenshots from the session
- LangSmith trace URL (if available)

### Common Error Messages

| Error | Meaning | Solution |
|-------|---------|----------|
| "No 'refined_prompt' found in JSON" | Input file missing required key | Add `refined_prompt` to JSON |
| "Connection to Blender lost" | Blender disconnected | Restart Blender, reload addon |
| "RuntimeError: Attempted to exit cancel scope" | Async cleanup issue | **FIXED** - Update to latest code |
| "Rate limit exceeded" | Too many API calls | Use shorter prompts, concise mode |

### Performance Tips
- **First run slower**: MCP server initialization takes ~10s
- **Screenshot capture**: Each takes 1-2s
- **LLM planning**: Depends on requirement complexity
- **Tool execution**: Varies by Blender operation

Expected timing for typical model:
- Planning: 5-15s
- Execution: 30-120s per step
- Screenshot: 2s each
- Total: 1-5 minutes for simple models
