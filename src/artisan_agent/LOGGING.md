# Sample Artisan Agent Log File

This is an example of what gets logged when running the Artisan Agent.

**Log file format:** `artisan_agent_YYYYMMDD_HHMMSS_<session_id>.log`

**Example:** `artisan_agent_20251127_180314_bf37c46d.log`

## Sample Log Content

```log
2025-11-27 18:03:14 - __main__ - INFO - Logging initialized - Log file: data/logs/artisan_agent_20251127_180314_bf37c46d.log
2025-11-27 18:03:14 - __main__ - INFO - Session ID: bf37c46d-920f-48cc-9fe8-2e22f8105a51
2025-11-27 18:03:14 - __main__ - INFO - Verbose mode: False
2025-11-27 18:03:14 - __main__ - INFO - ================================================================================
2025-11-27 18:03:14 - __main__ - INFO - ARTISAN AGENT - Autonomous 3D Modeling
2025-11-27 18:03:14 - __main__ - INFO - ================================================================================
2025-11-27 18:03:14 - __main__ - INFO - Input File: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
2025-11-27 18:03:14 - __main__ - INFO - Session ID: bf37c46d-920f-48cc-9fe8-2e22f8105a51
2025-11-27 18:03:14 - __main__ - INFO - Log File: data/logs/artisan_agent_20251127_180314_bf37c46d.log
2025-11-27 18:03:14 - __main__ - INFO - --------------------------------------------------------------------------------
2025-11-27 18:03:14 - __main__ - INFO - Initializing Artisan Agent...
2025-11-27 18:03:14 - BlenderMCPServer - INFO - BlenderMCP server starting up
2025-11-27 18:03:14 - BlenderMCPServer - INFO - Connected to Blender at localhost:9876
2025-11-27 18:03:14 - BlenderMCPServer - INFO - Created new persistent connection to Blender
2025-11-27 18:03:14 - BlenderMCPServer - INFO - Successfully connected to Blender on startup
2025-11-27 18:03:14 - mcp.server.lowlevel.server - INFO - Processing request of type ListToolsRequest
2025-11-27 18:03:14 - __main__ - INFO - Agent initialized successfully
2025-11-27 18:03:14 - __main__ - INFO - Starting modeling task from: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
2025-11-27 18:03:42 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Sending command: get_polyhaven_status with params: None
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Command sent, waiting for response...
2025-11-27 18:03:42 - BlenderMCPServer - ERROR - Socket connection error during receive: [Errno 104] Connection reset by peer
2025-11-27 18:03:42 - BlenderMCPServer - WARNING - Existing connection is no longer valid: Connection to Blender lost
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Connected to Blender at localhost:9876
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Created new persistent connection to Blender
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Sending command: get_viewport_screenshot with params: {'max_size': 800, 'format': 'png'}
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Command sent, waiting for response...
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Received complete response (383638 bytes)
2025-11-27 18:03:42 - BlenderMCPServer - INFO - Response parsed, status: success
2025-11-27 18:04:42 - mcp.server.lowlevel.server - INFO - Processing request of type CallToolRequest
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Sending command: get_polyhaven_status with params: None
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Command sent, waiting for response...
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Received complete response (382 bytes)
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Response parsed, status: success
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Sending command: get_scene_info with params: None
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Command sent, waiting for response...
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Received complete response (305 bytes)
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Response parsed, status: success
2025-11-27 18:04:42 - __main__ - INFO - Modeling task completed
2025-11-27 18:04:42 - __main__ - INFO - ================================================================================
2025-11-27 18:04:42 - __main__ - INFO - MODELING RESULTS
2025-11-27 18:04:42 - __main__ - INFO - ================================================================================
2025-11-27 18:04:42 - __main__ - INFO - Success: True
2025-11-27 18:04:42 - __main__ - INFO - Steps Executed: 0
2025-11-27 18:04:42 - __main__ - INFO - Screenshots Captured: 1
2025-11-27 18:04:42 - __main__ - INFO - Screenshot Directory: data/blender/screenshots/bf37c46d-920f-48cc-9fe8-2e22f8105a51
2025-11-27 18:04:42 - __main__ - INFO - Session ID: bf37c46d-920f-48cc-9fe8-2e22f8105a51
2025-11-27 18:04:42 - __main__ - INFO - Starting cleanup...
2025-11-27 18:04:42 - BlenderMCPServer - INFO - Disconnecting from Blender on shutdown
2025-11-27 18:04:42 - BlenderMCPServer - INFO - BlenderMCP server shut down
2025-11-27 18:04:42 - __main__ - INFO - Cleanup completed successfully
2025-11-27 18:04:42 - __main__ - INFO - ================================================================================
2025-11-27 18:04:42 - __main__ - INFO - Session completed - Log saved to: data/logs/artisan_agent_20251127_180314_bf37c46d.log
2025-11-27 18:04:42 - __main__ - INFO - ================================================================================
```

## Log Levels

### INFO Level (Default)
Shows major events:
- Session initialization
- Agent startup
- Task execution milestones
- Results summary
- Cleanup operations

### DEBUG Level (--verbose flag)
Shows detailed information:
- Full tool arguments
- Complete API responses
- Detailed error tracebacks
- Internal state changes
- Performance metrics

## Verbose Mode Example

Run with `--verbose` flag:
```bash
python src/artisan_agent/run_artisan.py -i your_file.json --verbose
```

Additional logs in verbose mode:
```log
2025-11-27 18:04:42 - __main__ - DEBUG - Tool call: execute_blender_code
2025-11-27 18:04:42 - __main__ - DEBUG - Arguments: {'code': 'import bpy\nbpy.ops.object.select_all(action="SELECT")\nbpy.ops.object.delete()'}
2025-11-27 18:04:42 - __main__ - DEBUG - Result: {'status': 'success', 'output': 'Objects deleted'}
2025-11-27 18:04:42 - __main__ - INFO - --------------------------------------------------------------------------------
2025-11-27 18:04:42 - __main__ - INFO - TOOL EXECUTION SUMMARY
2025-11-27 18:04:42 - __main__ - INFO - --------------------------------------------------------------------------------
2025-11-27 18:04:42 - __main__ - INFO - 1. [SUCCESS] execute_blender_code
2025-11-27 18:04:42 - __main__ - INFO -    Arguments: {'code': 'import bpy\nbpy.ops.object.select_all(action="SELECT")...'}
```

## Error Logging

When errors occur:
```log
2025-11-27 18:05:15 - __main__ - ERROR - Error occurred: Connection to Blender failed
2025-11-27 18:05:15 - __main__ - ERROR - Full traceback:
2025-11-27 18:05:15 - __main__ - ERROR - Traceback (most recent call last):
2025-11-27 18:05:15 - __main__ - ERROR -   File "run_artisan.py", line 123, in main
2025-11-27 18:05:15 - __main__ - ERROR -     await agent.initialize()
2025-11-27 18:05:15 - __main__ - ERROR - ConnectionError: Failed to connect to Blender at localhost:9876
```

## Log File Benefits

1. **Audit Trail** - Complete record of all operations
2. **Debugging** - Detailed error information with timestamps
3. **Performance** - Track execution time of each step
4. **Reproducibility** - Exact sequence of operations recorded
5. **Troubleshooting** - Send log file when reporting issues

## Log Retention

- Each run creates a new log file
- Files are timestamped for easy identification
- Session ID in filename links log to screenshots
- Consider cleaning old logs periodically

## Integration with LangSmith

Logs complement LangSmith traces:
- **Logs**: Local file with complete session record
- **LangSmith**: Cloud-based trace visualization with LLM internals
- **Together**: Complete debugging solution

Find your session in LangSmith using the session ID from the log file.
