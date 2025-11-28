# Changelog

## [1.1.2] - 2025-11-27

### Fixed
- **Critical: Tool conversation flow error** - "tool_use ids were found without tool_result blocks"
  - After executing tools, the agent now properly adds `ToolMessage` objects to conversation history
  - Each tool execution now creates a corresponding ToolMessage with tool_call_id
  - Fixes Anthropic API error preventing multi-step workflows from executing
  - Agent can now successfully execute all 12 planned steps

- **Critical: LangGraph recursion limit exceeded** - "Recursion limit of 25 reached"
  - Increased recursion limit from default 25 to 100
  - Allows multi-step workflows (12+ steps) to complete
  - Each workflow step requires ~4 graph iterations (plan → execute → capture → evaluate)
  - Config now includes `recursion_limit: 100` for all agent runs

### Technical Details
The Anthropic API requires that every `tool_use` block in an AI message be followed by a `tool_result` block in the next user/tool message. Previously, the agent was:
1. Getting AI response with tool_use
2. Executing the tool
3. Adding only the AI response to messages
4. Trying to send next message → ERROR

Now the agent:
1. Gets AI response with tool_use  
2. Executes the tool
3. Adds AI response to messages
4. **Adds ToolMessage with results to messages**
5. Next message works correctly ✅

## [1.1.1] - 2025-11-27

### Fixed
- **Planning step parsing failure** - Agent was completing with 0 steps executed
  - Improved step parsing with multiple pattern recognition (1., 1), Step 1:, etc.)
  - Added fallback plan when LLM response parsing fails (5 generic steps)
  - Better prompt to LLM with explicit formatting instructions
  - Truncate very long requirements to prevent token issues

### Added
- **Extensive logging throughout agent workflow**
  - Planning node logs LLM response and parsed steps
  - Execute node logs current step, tool calls, and results  
  - Evaluate node logs progress and completion status
  - Tool execution logs success/failure with error details
  - Warning when LLM doesn't request any tool calls

### Changed
- **`_plan_node`** improvements:
  - Better step parsing with multiple numbering formats
  - Fallback to generic 5-step plan if parsing fails
  - Truncate requirement to 1000 chars for planning prompt
  - Request 5-10 steps explicitly in prompt
  - Log LLM response length and content

- **`_execute_step_node`** improvements:
  - Log current step index and total steps
  - Log each tool call with arguments
  - Log tool execution results
  - Warn if LLM returns no tool calls

- **`_evaluate_progress_node`** improvements:
  - Log evaluation decision
  - Log remaining steps count

### Documentation
- Updated **TROUBLESHOOTING.md** with detailed "No Planning Steps Created" section
  - Explains root cause
  - Shows how to debug with verbose mode
  - Documents fallback behavior
  - Provides expected outcomes

## [1.1.0] - 2025-11-27

### Added
- **Comprehensive logging system** for Artisan Agent CLI
  - All operations logged to `data/logs/artisan_agent_YYYYMMDD_HHMMSS_<session_id>.log`
  - Dual output: console + log file
  - Configurable log levels: INFO (default) and DEBUG (--verbose)
  - Session tracking with unique log files per run
  - Detailed error logging with full tracebacks in verbose mode
  - Log file path displayed at startup and completion
  - Logs include: initialization, planning, tool execution, screenshots, errors, cleanup

- **Enhanced session management**
  - Session ID auto-generated if not provided
  - Log files use first 8 chars of session ID for readability
  - All logging initialized before agent execution

### Changed
- **run_artisan.py** - Major enhancements:
  - Added `logging` and `datetime` imports
  - New `setup_logging()` function with file and console handlers
  - Session ID generated early for logging setup
  - All major operations now logged (initialization, execution, cleanup, errors)
  - Log file path displayed in startup banner
  - Verbose mode provides DEBUG-level logging with full tracebacks
  - Cleanup errors logged but suppressed
  - Final log message shows log file location

### Documentation
- Updated **README.md** - Added "Logging" section
  - Documented log file naming convention
  - Explained log levels and verbose mode
  - Listed what gets logged
  - Provided example log file name

- Updated **CHANGELOG.md** - Added v1.1.0 release notes

## [1.0.1] - 2025-11-27

### Fixed
- **RuntimeError during async cleanup** - Enhanced exception handling for MCP stdio_client cleanup
  - Added specific handling for `RuntimeError`, `GeneratorExit`, and `BaseExceptionGroup`
  - Wrapped all cleanup operations in try-except blocks
  - Added 0.1s delay after cleanup to allow async tasks to finish gracefully
  - Prevents duplicate cleanup with `_cleanup_done` flag
  - Error is now suppressed - was cosmetic and didn't affect functionality

### Changed
- **Cleanup error handling** in `BlenderMCPConnection.cleanup()`
  - Session context cleanup now catches all exceptions
  - Stdio context cleanup now catches all exceptions
  - Both contexts properly closed in correct order (session first, then stdio)

- **Agent cleanup** in `run_artisan.py`
  - Added try-except wrapper around `agent.cleanup()`
  - Added post-cleanup async sleep to allow graceful shutdown

- **Streamlit cleanup** in `streamlit_artisan.py`
  - Added try-except wrapper around `agent.cleanup()`
  - Ensures UI doesn't show error messages on normal exit

### Documentation
- Created **TROUBLESHOOTING.md** - Comprehensive troubleshooting guide
  - RuntimeError explanation and solution
  - Connection reset by peer handling
  - Common issues and solutions
  - Best practices for debugging
  - Performance optimization tips

- Updated **README.md**
  - Added reference to troubleshooting guide
  - Added "Additional Documentation" section
  - Noted RuntimeError as fixed

## [1.0.0] - 2025-11-27

### Added
- **Initial release** of Artisan Agent
- Autonomous 3D modeling agent using LangGraph and Claude Sonnet 4.5
- Plan → Execute → Capture → Evaluate → Complete workflow
- Screenshot capture with session-based organization
- CLI interface with argparse (`run_artisan.py`)
- Streamlit web interface (`streamlit_artisan.py`)
- LangSmith integration for complete tracing
- MCP (Model Context Protocol) integration for Blender control
- Comprehensive documentation (README, QUICKSTART, IMPLEMENTATION)
- Usage examples demonstrating 6 integration patterns
- Test script with example JSON file

### Features
- Read requirements from JSON files in `data/prompts/json/`
- Autonomous planning and step execution
- Visual feedback through viewport screenshots
- Session-based screenshot organization
- Support for both CLI and Streamlit interfaces
- Complete LangSmith tracing with `@traceable` decorators
- Error handling and recovery
- Progress display in console and Streamlit
- Tool execution result tracking

### Dependencies
- LangChain 0.3+
- LangGraph 0.2+
- LangSmith 0.2+
- Anthropic Claude API
- MCP Python SDK 1.3+
- Streamlit 1.51+
- Python 3.11+

### Documentation
- README.md - Overview and architecture
- QUICKSTART.md - 5-minute quick start
- IMPLEMENTATION.md - Technical details
- examples.py - 6 programmatic usage examples
- test_agent.py - Test script with sample data
