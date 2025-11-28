# Session Resume Feature

## Overview

The Artisan Agent now supports **automatic session continuation**, allowing it to resume modeling tasks from where they stopped in previous runs. This is especially useful when:

- The recursion limit is reached before completing all steps
- You need to stop and restart the agent
- Blender crashes or disconnects mid-session
- You want to iteratively refine a model across multiple runs

## How It Works

### 1. Deterministic Session IDs

Instead of random UUIDs, the agent generates session IDs based on the **input file path**:

```python
# Same input file = same session ID
session_id = hashlib.sha256(absolute_file_path).hexdigest()[:16]
```

This ensures that running the same JSON file multiple times uses the **same session ID**, allowing the agent to resume previous work.

### 2. Scene Analysis Node

On every run, the agent starts with a **scene analysis** phase:

```
analyze_scene → plan → execute_step → capture_feedback → evaluate_progress → complete
```

The `analyze_scene` node:
- Captures the current viewport screenshot
- Gets scene information (objects, properties)
- Detects if there's existing work in the scene
- Saves initial state for comparison

### 3. Progress Detection

When existing objects are detected in the scene, the agent:

1. **Plans the full task** based on requirements
2. **Inspects objects in detail** using `get_object_info` to check vertex counts, modifiers, materials
3. **Asks the LLM** which steps have SUBSTANTIAL completed geometry (not just placeholders)
4. **Applies safety limits** - won't skip more than 30% of steps to avoid false positives
5. **Skips completed steps** and resumes from the next one

**Conservative Detection Criteria:**
- Objects must have substantial geometry (not empty curves or basic primitives)
- Looks for modifiers, particle systems, complex meshes, applied materials
- Placeholder objects (named but empty) do NOT count as completed
- When in doubt, marks step as NOT done to avoid skipping important work

Example:
```
Planned Steps:
1. Clear scene and create base trunk cylinder
2. Add branch geometry with array modifier  
3. Apply pine needle particle system
4. Add materials and textures
5. Position lighting and camera

Current Scene: Contains trunk cylinder, branch array applied, no particles

LLM Detection: Steps 1,2 completed
Resume Point: Starting from step 3 (particle system)
```

### 4. Smart Step Skipping

The agent maintains two lists:
- `completed_steps[]`: Steps already done (detected via scene analysis)
- `planning_steps[]`: All steps needed to complete the task
- `current_step`: Index of next step to execute

When resuming:
```python
if scene_has_objects:
    detect_completed_steps()  # LLM analyzes scene vs. plan
    current_step = max(completed_indices) + 1
    skip_to_next_incomplete_step()
```

## Usage

### CLI - Default Behavior (Resume Enabled)

```bash
# First run - builds until recursion limit (step 1-25)
python src/artisan_agent/run_artisan.py -i data/prompts/json/christmas_tree.json

# Second run - analyzes scene, detects steps 1-25 done, continues from step 26
python src/artisan_agent/run_artisan.py -i data/prompts/json/christmas_tree.json
```

### CLI - Disable Resume (Fresh Start)

```bash
# Force fresh start even if scene has existing work
python src/artisan_agent/run_artisan.py -i data/prompts/json/christmas_tree.json --no-resume
```

### Streamlit UI

1. Check **"Enable Resume Mode"** (default: enabled)
2. Select your JSON file
3. Click "Start Modeling"

If the scene contains partial work:
- Resume mode ON: Continues from breakpoint
- Resume mode OFF: Starts fresh (but doesn't clear scene)

### Programmatic Usage

```python
from src.artisan_agent import ArtisanAgent

agent = ArtisanAgent()
await agent.initialize()

# Resume enabled (default)
results = await agent.run("path/to/requirement.json", use_deterministic_session=True)

# Fresh start with random session ID
results = await agent.run("path/to/requirement.json", use_deterministic_session=False)
```

## Session ID Examples

### With Resume (Deterministic)

```bash
# Run 1
Input: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
Session ID: a3f8c9e1d4b2f5a7  # Hash of file path
Screenshots: data/blender/screenshots/a3f8c9e1d4b2f5a7/

# Run 2 (same file)
Input: data/prompts/json/20251127_135557_Could_you_model_a_ch.json
Session ID: a3f8c9e1d4b2f5a7  # Same hash = same session
Screenshots: data/blender/screenshots/a3f8c9e1d4b2f5a7/  # Same folder
```

### Without Resume (Random)

```bash
# Run 1
Session ID: 3a7f9c2e-4b1d-8f5a-9e2c-6d4f1a8b3e7c  # Random UUID

# Run 2 (same file)
Session ID: 8e2d4f1a-9c3b-5e7f-2a4d-1f8c9e3b7a6d  # Different UUID
```

## Log Output Examples

### Fresh Start (No Existing Work)

```
📄 Input File: data/prompts/json/christmas_tree.json
🔑 Session ID: a3f8c9e1d4b2f5a7
🔄 Resume Mode: Enabled

ℹ️ Analyzing current scene state...
📸 Initial scene captured
ℹ️ Scene objects detected: False
ℹ️ Starting fresh - no existing work detected

📋 Planning modeling steps...
✅ Created 12-step plan
  1. Clear default scene and set up environment
  2. Create trunk cylinder with proper dimensions
  ...
```

### Resumed Session (Existing Work Found)

```
📄 Input File: data/prompts/json/christmas_tree.json
🔑 Session ID: a3f8c9e1d4b2f5a7
🔄 Resume Mode: Enabled

ℹ️ Analyzing current scene state...
📸 Initial scene captured
ℹ️ Scene objects detected: True
🤔 Detected existing work - planning to resume

📋 Planning modeling steps...
🤔 Detecting completed work...
✅ Resuming from step 6 (skipped 5 completed)
✅ Created 12-step plan

✓ Skipping 5 completed steps
  ✓ 1. Clear default scene and set up environment
  ✓ 2. Create trunk cylinder with proper dimensions
  ✓ 3. Add branch array modifier
  ✓ 4. Create needle particle system
  ✓ 5. Apply base materials

  6. Add detailed bark texture with displacement
  7. Refine needle material with subsurface scattering
  ...
```

## Technical Details

### State Fields Added

```python
class AgentState(TypedDict):
    # ... existing fields ...
    initial_scene_state: Dict[str, Any]  # Scene snapshot at start
    completed_steps: List[str]           # Steps already done
    is_resuming: bool                    # True if continuing previous work
```

### Workflow Graph Updated

```
Old: plan → execute_step → capture_feedback → evaluate_progress

New: analyze_scene → plan → execute_step → capture_feedback → evaluate_progress
```

### LLM Prompts Enhanced

**Planning with Scene Context:**
```
Requirement: Build a Christmas tree...

CURRENT SCENE STATE:
Objects: ['Trunk', 'BranchArray', 'NeedleParticles']
Materials: ['BarkMaterial']

IMPORTANT: The scene already contains objects. Analyze what's been done 
and continue building from there. Do NOT start from scratch.
```

**Progress Detection:**
```
Based on the current scene state, identify which of these planned steps 
appear to be already completed:

Planned Steps:
1. Clear scene
2. Create trunk
3. Add branches
...

Current Scene:
Objects: ['Trunk', 'BranchArray']
...

Respond with ONLY the step numbers that are already done (e.g., "1,2,3")
```

## Benefits

### 1. Recursion Limit Handling
- **Before**: Hit limit at step 25, task incomplete, must restart from scratch
- **After**: Hit limit at step 25, resume continues from step 26

### 2. Iterative Refinement
```bash
# Run 1: Basic structure
python run_artisan.py -i tree.json
# Result: Basic trunk and branches created

# Run 2: Add details (analyzes scene, continues)
python run_artisan.py -i tree.json
# Result: Needles, materials, lighting added
```

### 3. Error Recovery
- Blender crash: Reopen, re-run agent → continues from last checkpoint
- Network issue: Reconnect → agent resumes
- Manual adjustments: Make changes in Blender → agent detects and adapts

### 4. Consistent Sessions
- Same input file always uses same session ID
- Screenshots organized in same folder across runs
- Easy to track progress over multiple iterations

## Limitations

### 1. Scene Analysis Accuracy
The LLM's step detection is **conservative** - it only marks steps as complete if there's clear evidence in the scene. This means:
- May occasionally re-execute already-done steps (safe)
- Won't skip steps that aren't fully complete (correct behavior)

### 2. Manual Scene Changes
If you manually modify the scene between runs, the agent will:
- Detect the changes in scene analysis
- Attempt to continue based on current state
- May produce unexpected results if changes don't align with plan

**Recommendation**: Use `--no-resume` if you've manually edited the scene significantly.

### 3. Requirement Changes
Changing the requirement while keeping the same filename:
- Agent uses same session ID (based on filename)
- May detect "completed" work that doesn't match new requirements
- Can lead to confused behavior

**Recommendation**: Use different filenames for different requirements, or use `--no-resume`.

## Best Practices

### ✅ Good Use Cases
- Long tasks that exceed recursion limit
- Iterative model refinement
- Testing and debugging agent behavior
- Recovery from crashes or interruptions

### ⚠️ Use Caution
- After manual Blender edits (consider `--no-resume`)
- When changing requirements in same file
- When you want completely fresh start every time

### 🔧 Troubleshooting

**Agent keeps re-doing same steps:**
- Check logs to see what LLM detected as completed
- Scene may be ambiguous - add more distinctive objects
- Try `--no-resume` to start fresh

**Agent skips important steps:**
- LLM may have incorrectly detected completion
- Check initial scene screenshot in logs
- File issue if detection logic needs improvement

**Session ID collision:**
- Different files mapping to same ID (very rare with SHA-256)
- Manually specify session ID: `-s my-unique-id`

## Configuration

### Environment Variables

```bash
# Maximum graph iterations (includes resume detection overhead)
LANGGRAPH_RECURSION_LIMIT=100
```

### CLI Arguments

```bash
--resume          # Enable resume (default)
--no-resume       # Disable resume, always fresh start
--session-id, -s  # Override deterministic session ID
```

### Programmatic

```python
# Enable resume
agent.run(file_path, use_deterministic_session=True)

# Disable resume  
agent.run(file_path, use_deterministic_session=False)

# Manual session ID
agent = ArtisanAgent(session_id="my-custom-session")
agent.run(file_path, use_deterministic_session=False)
```

## Version History

- **v1.2.0**: Added session resume capability
  - Deterministic session IDs from file hash
  - Scene analysis node
  - LLM-based progress detection
  - Smart step skipping
  - Resume/no-resume CLI flags
  - Streamlit UI toggle

---

**Last Updated**: November 27, 2025  
**Author**: Artisan Agent Development Team  
**Status**: Production Ready
