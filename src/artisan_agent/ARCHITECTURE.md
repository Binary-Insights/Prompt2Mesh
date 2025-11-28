# Artisan Agent - Architecture Diagrams

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     ARTISAN AGENT SYSTEM                        │
└─────────────────────────────────────────────────────────────────┘

Input Layer:
┌──────────────────────┐
│  JSON Requirement    │  <- Created by Prompt Refinement Agent
│  (refined_prompt)    │     or manually crafted
└──────────┬───────────┘
           │
           ▼
Agent Layer:
┌──────────────────────────────────────────────────────────────┐
│                    ARTISAN AGENT                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              LangGraph Workflow                        │  │
│  │  ┌──────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │ Plan │→│ Execute  │→│ Capture  │→│ Evaluate │  │  │
│  │  └──────┘  │  Step    │  │ Feedback │  │ Progress │  │  │
│  │            └──────────┘  └──────────┘  └────┬─────┘  │  │
│  │                 ▲                            │        │  │
│  │                 │                            │        │  │
│  │                 └─────── continue ───────────┘        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  Claude Sonnet 4.5 | LangChain | LangSmith Tracing          │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
MCP Layer:
┌──────────────────────────────────────────────────────────────┐
│              Blender MCP Connection                          │
│  - execute_blender_code                                      │
│  - get_scene_info                                            │
│  - get_viewport_screenshot                                   │
│  - get_object_info                                           │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
Blender Layer:
┌──────────────────────────────────────────────────────────────┐
│                     BLENDER                                  │
│  - Create objects                                            │
│  - Modify materials                                          │
│  - Capture screenshots                                       │
│  - Export results                                            │
└──────────────────────────────────────────────────────────────┘

Output Layer:
┌──────────────────────┐      ┌──────────────────────┐
│   3D Model in        │      │    Screenshots       │
│   Blender Scene      │      │  (PNG images)        │
└──────────────────────┘      └──────────────────────┘
```

## LangGraph Workflow Detail

```
START
  │
  ▼
┌─────────────────────┐
│   plan_node         │
│                     │
│ - Read requirement  │
│ - Analyze task      │
│ - Create steps      │
│ - Store in state    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  execute_step_node  │◄──────────┐
│                     │           │
│ - Get current step  │           │
│ - Generate code     │           │
│ - Call MCP tools    │           │
│ - Store results     │           │
└─────────┬───────────┘           │
          │                       │
          ▼                       │
┌─────────────────────┐           │
│ capture_feedback_   │           │
│      node           │           │
│                     │           │
│ - Screenshot tool   │           │
│ - Save to disk      │           │
│ - Get scene info    │           │
│ - Update history    │           │
└─────────┬───────────┘           │
          │                       │
          ▼                       │
┌─────────────────────┐           │
│ evaluate_progress_  │           │
│      node           │           │
│                     │           │
│ - Check completion  │           │
│ - Count remaining   │           │
│ - Update state      │           │
└─────────┬───────────┘           │
          │                       │
          ├─ is_complete: False ──┘
          │    (continue loop)
          │
          ├─ is_complete: True
          │
          ▼
┌─────────────────────┐
│   complete_node     │
│                     │
│ - Finalize results  │
│ - Generate report   │
│ - Save metadata     │
└─────────┬───────────┘
          │
          ▼
         END
```

## State Flow

```
AgentState Evolution:

Initial State:
{
  messages: [HumanMessage("Create 3D model...")],
  requirement: "Full detailed specification...",
  session_id: "20251127_143022",
  screenshot_dir: Path("data/blender/screenshots/20251127_143022"),
  tool_results: [],
  screenshot_count: 0,
  planning_steps: [],
  current_step: 0,
  is_complete: False,
  feedback_history: []
}

After Planning:
{
  ...
  planning_steps: [
    "1. Clear scene and set units",
    "2. Create trunk cylinder",
    "3. Add branch geometry",
    ...
  ],
  current_step: 0
}

After First Execution:
{
  ...
  tool_results: [{
    "success": True,
    "tool_name": "execute_blender_code",
    "result": "Scene cleared",
    ...
  }],
  current_step: 1
}

After First Screenshot:
{
  ...
  screenshot_count: 1,
  feedback_history: [
    "Step 1 - Scene: Empty with grid..."
  ]
}

Final State:
{
  ...
  tool_results: [12 tool results],
  screenshot_count: 8,
  current_step: 12,
  is_complete: True,
  feedback_history: [8 feedback entries]
}
```

## Interface Comparison

```
┌──────────────────────────────────────────────────────────────┐
│                    CLI INTERFACE                             │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  $ python run_artisan.py -i input.json -v                   │
│                                                              │
│  Advantages:                                                 │
│  ✓ Scriptable / Automation                                  │
│  ✓ CI/CD integration                                        │
│  ✓ Background processing                                    │
│  ✓ Verbose logging                                          │
│  ✓ Exit codes for error handling                           │
│                                                              │
│  Use Cases:                                                  │
│  - Batch processing                                          │
│  - Scheduled jobs                                            │
│  - Server deployments                                        │
│  - Development/testing                                       │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                STREAMLIT INTERFACE                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  $ streamlit run streamlit_artisan.py                        │
│                                                              │
│  Advantages:                                                 │
│  ✓ Visual file browser                                      │
│  ✓ Requirement preview                                      │
│  ✓ Real-time progress display                               │
│  ✓ Screenshot gallery                                       │
│  ✓ Interactive controls                                     │
│  ✓ Detailed results view                                    │
│                                                              │
│  Use Cases:                                                  │
│  - Interactive modeling                                      │
│  - Demo/presentation                                         │
│  - Result visualization                                      │
│  - Client-facing interface                                  │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
JSON File (Input)
       │
       │ read "refined_prompt"
       ▼
  Agent State
       │
       │ analyze with Claude
       ▼
Planning Steps (List[str])
       │
       ├─► Step 1 ──► execute_blender_code ──► Blender
       │                      │
       │                      ▼
       │               Tool Result ──► State
       │                      │
       │                      ▼
       │            get_viewport_screenshot ──► PNG
       │                      │
       │                      ▼
       │                Screenshot File ──► Disk
       │                      │
       │                      ▼
       │                Scene Info ──► State
       │
       ├─► Step 2 ──► ...
       │
       ├─► Step 3 ──► ...
       │
       └─► Step N ──► Complete
                      │
                      ▼
               Final Results
                      │
                      ├─► 3D Model (Blender)
                      ├─► Screenshots (PNG files)
                      └─► Report (Dict)
```

## Screenshot Management

```
Session Start
     │
     ├─ Generate session_id: "20251127_143022"
     │
     ├─ Create directory: data/blender/screenshots/20251127_143022/
     │
     ├─ During execution:
     │      │
     │      ├─ Step 1 complete ──► screenshot_0.png
     │      │                       step_1_screenshot_0.png
     │      │
     │      ├─ Step 3 complete ──► screenshot_1.png
     │      │                       step_3_screenshot_1.png
     │      │
     │      ├─ Step 5 complete ──► screenshot_2.png
     │      │                       step_5_screenshot_2.png
     │      │
     │      └─ ...
     │
     └─ Session end:
            Directory contains:
            ├─ step_1_screenshot_0.png
            ├─ step_3_screenshot_1.png
            ├─ step_5_screenshot_2.png
            └─ ...
```

## Tool Call Sequence Example

```
Requirement: "Create a Christmas tree"

Plan → 12 Steps

Step 1: "Clear scene and set units"
    ├─► execute_blender_code(code="import bpy; bpy.ops.object.select_all(...)")
    │   └─► Result: Success
    └─► get_viewport_screenshot()
        └─► Result: step_1_screenshot_0.png

Step 2: "Create trunk cylinder"
    ├─► execute_blender_code(code="bpy.ops.mesh.primitive_cylinder_add(...)")
    │   └─► Result: Success
    └─► get_viewport_screenshot()
        └─► Result: step_2_screenshot_1.png

Step 3: "Create bottom tier of branches"
    ├─► execute_blender_code(code="for i in range(8): ...")
    │   └─► Result: Success
    └─► get_viewport_screenshot()
        └─► Result: step_3_screenshot_2.png

...

Step 12: "Final setup and render settings"
    ├─► execute_blender_code(code="bpy.context.scene.render...")
    │   └─► Result: Success
    ├─► get_viewport_screenshot()
    │   └─► Result: step_12_screenshot_11.png
    └─► Complete!

Result:
    - 12 steps executed
    - 12 tool calls to execute_blender_code
    - 12 tool calls to get_viewport_screenshot
    - 12 PNG files saved
    - 1 complete 3D model in Blender
```

## Error Handling Flow

```
Tool Call
    │
    ├─ Success?
    │    ├─ Yes → Continue to next step
    │    └─ No  → Log error, store in tool_results
    │              │
    │              ├─ Critical error? (connection lost)
    │              │    └─ Stop execution, cleanup
    │              │
    │              └─ Non-critical? (object not found)
    │                   └─ Continue with next step
    │
    ├─ Timeout?
    │    └─ Retry logic (future enhancement)
    │
    └─ Exception?
         └─ Catch, log, store, continue or stop
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                 EXTERNAL INTEGRATIONS                       │
└─────────────────────────────────────────────────────────────┘

LangSmith:
    All @traceable functions → traces on smith.langchain.com
    
Prompt Refinement Agent:
    Generates JSON files → Artisan Agent consumes
    
Backend API (Future):
    FastAPI endpoint → POST /model → Artisan Agent → Response
    
File System:
    Reads: data/prompts/json/*.json
    Writes: data/blender/screenshots/{session_id}/*.png
    
Blender:
    Via MCP: localhost:9876
    Commands: Python code execution
    Responses: JSON results, base64 images
```

## Execution Timeline

```
T=0s:    Agent initialization
         └─► Connect to Blender MCP

T=2s:    Planning phase
         └─► Claude analyzes requirement
         └─► Generates 12-step plan

T=5s:    Step 1 execution
         ├─► execute_blender_code
         ├─► get_viewport_screenshot
         └─► Evaluate progress

T=8s:    Step 2 execution
         └─► ...

T=11s:   Step 3 execution
         └─► ...

...

T=45s:   Step 12 execution
         └─► Final screenshot

T=47s:   Complete!
         ├─► Save results
         ├─► Generate report
         └─► Cleanup MCP connection
```

This architecture enables autonomous, traceable, and robust 3D modeling!
