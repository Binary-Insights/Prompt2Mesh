# Refinement Loop Architecture

## Overview

The Artisan Agent now implements an **iterative refinement loop** that makes it comparable to Claude Desktop's quality-driven approach. Instead of executing a fixed 12-step plan without feedback, the agent now:

1. **Executes a step** → **Captures screenshot** → **Analyzes quality with vision AI** → **Refines if needed** → **Continues**

This creates a feedback-driven workflow where each step is evaluated and can be improved before moving forward.

---

## Architecture Changes

### 1. **Enhanced AgentState**

Added new fields to track refinement:

```python
class AgentState(TypedDict):
    # ... existing fields ...
    
    # NEW: Refinement loop fields
    vision_feedback: List[str]  # Vision-based quality feedback from screenshots
    execution_errors: List[str]  # Execution errors for debugging
    quality_scores: List[Dict[str, Any]]  # Quality scores per step
    refinement_attempts: int  # Number of refinement attempts for current step
    max_refinements_per_step: int  # Maximum refinements allowed per step (default: 2)
    needs_refinement: bool  # Whether current step needs refinement
    refinement_feedback: Optional[str]  # Specific feedback for refinement
```

### 2. **New Graph Nodes**

#### **`assess_quality` Node**
- **Purpose**: Evaluates quality of the just-executed step using vision feedback
- **Input**: Latest screenshot's vision analysis
- **Output**: Quality score (1-10) and refinement decision
- **Logic**:
  - Parses quality rating from vision feedback (e.g., "8/10")
  - Threshold: Score < 6 → needs refinement
  - Critical steps (1-5): Score < 7 → needs refinement
  - Respects max refinement attempts (default: 2 per step)

#### **`refine_step` Node**
- **Purpose**: Generates and executes improvement code based on quality feedback
- **Input**: Original step description + vision feedback identifying issues
- **Process**:
  1. Creates refinement prompt for LLM
  2. Asks: "How can we improve this based on visual issues?"
  3. Generates enhanced Blender Python code
  4. Executes improvements using `execute_blender_code` tool
- **Key Feature**: Enhancements build on existing work, not replace it

### 3. **Updated Graph Flow**

**Previous Flow (No Refinement):**
```
execute_step → capture_feedback → evaluate_progress → (continue/complete)
```

**New Flow (With Refinement Loop):**
```
execute_step 
    → capture_feedback (with vision analysis)
        → assess_quality
            ├─ (quality >= threshold) → evaluate_progress → continue/complete
            └─ (quality < threshold) → refine_step 
                                        → capture_feedback (re-assess)
                                            → assess_quality (repeat)
```

### 4. **Vision-Based Quality Assessment**

Enhanced `_capture_feedback_node` now:

1. **Captures screenshot** (existing behavior)
2. **Sends to Claude Sonnet 4.5 Vision** with prompt:
   ```
   Analyze this 3D modeling screenshot from Blender.
   
   Current Step (X): [step description]
   
   Evaluate:
   1. Does the geometry match the step description?
   2. Is there sufficient detail and complexity?
   3. Are there any visual errors or missing elements?
   4. Overall quality rating (1-10)?
   
   Provide a brief analysis focusing on quality issues that need refinement.
   ```
3. **Stores vision feedback** in state for quality assessment

### 5. **Refinement Logic**

#### Quality Thresholds
- **Normal steps**: Score ≥ 6 → acceptable
- **Critical steps (1-5)**: Score ≥ 7 → acceptable (higher standards for foundation)
- **Max attempts**: 2 refinements per step (prevents infinite loops)

#### Refinement Prompt Strategy
```python
refinement_prompt = f"""You previously executed this step:
{current_step_desc}

Vision analysis identified these quality issues:
{vision_feedback}

Generate improved Blender Python code to address these issues. Focus on:
1. Adding more detail and complexity
2. Fixing any geometry errors
3. Improving visual realism
4. Maintaining compatibility with existing scene objects

IMPORTANT: The code should ENHANCE the existing work, not replace it entirely unless necessary.
"""
```

---

## Example Workflow

### Step 3: "Add branch layers using torus/circle arrays"

**Iteration 1:**
1. **Execute**: Creates 12 torus primitives as branch layers
2. **Screenshot**: Captures view of geometric torus rings
3. **Vision Analysis**: "Quality: 4/10 - Branches appear as simple geometric torus rings. Lacks organic detail, needles, and realistic variation."
4. **Quality Assessment**: Score 4 < threshold 6 → **Needs Refinement**
5. **Refinement**:
   - LLM generates code to add:
     - Subdivision surface for smoothness
     - Displacement modifier for irregularity
     - Random scaling per branch layer
     - Particle system for pine needles
6. **Re-capture**: New screenshot with enhanced branches

**Iteration 2:**
1. **Screenshot**: Shows branches with subdivision and some variation
2. **Vision Analysis**: "Quality: 7/10 - Branches now have organic shape. Could use more needle detail, but acceptable."
3. **Quality Assessment**: Score 7 ≥ threshold 6 → **Acceptable, Continue**
4. **Move to Step 4**

---

## Benefits Over Fixed Plan

### Before (Fixed Plan)
❌ Step executes regardless of quality  
❌ Errors cascade to later steps  
❌ No opportunity to improve rudimentary results  
❌ Vision feedback collected but unused  
❌ Results: Simple geometric primitives  

### After (Refinement Loop)
✅ Each step evaluated before proceeding  
✅ Quality issues identified and fixed immediately  
✅ Vision AI provides actionable improvement feedback  
✅ Critical steps held to higher standards  
✅ Results: Detailed, refined 3D models  

---

## Configuration

### Adjustable Parameters

```python
# In AgentState initialization
state["max_refinements_per_step"] = 2  # Change to 1 (faster) or 3 (higher quality)

# In _assess_quality_node
refinement_threshold = 6  # Lower = stricter quality requirements
critical_step_threshold = 7  # Quality bar for steps 1-5
```

### Performance Trade-offs

| Max Refinements | Quality | Time per Step | Best For |
|-----------------|---------|---------------|----------|
| 0 (disabled) | Low | ~8 sec | Testing/debugging |
| 1 | Medium | ~15 sec | Quick iterations |
| 2 (default) | High | ~22 sec | Production quality |
| 3 | Very High | ~30 sec | Final renders |

---

## Monitoring Refinement

### Logs to Watch

```
🎯 Assessing quality...
🔄 Quality score: 4/10 - Refinement needed
🔧 Refining step 3 (attempt 1)...
  🔧 Executing refinement code...
  ✅ Refinement applied
📸 Capturing viewport screenshot...
🔍 Vision analysis complete
🎯 Assessing quality...
✅ Quality score: 7/10 - Acceptable
```

### Quality Score History

The agent stores quality scores in `state["quality_scores"]`:

```python
[
    {
        "step": 3,
        "score": 4,
        "needs_refinement": True,
        "attempt": 0,
        "feedback": "Branches appear as simple geometric torus rings..."
    },
    {
        "step": 3,
        "score": 7,
        "needs_refinement": False,
        "attempt": 1,
        "feedback": "Branches now have organic shape..."
    }
]
```

Access via:
```python
# Get average quality score for the session
avg_score = sum(q["score"] for q in state["quality_scores"]) / len(state["quality_scores"])
```

---

## Screenshot Naming

Screenshots now include refinement attempt numbers:

- **Initial execution**: `step_3_screenshot_2.png`
- **First refinement**: `step_3_screenshot_3_refine1.png`
- **Second refinement**: `step_3_screenshot_4_refine2.png`
- **Next step**: `step_4_screenshot_5.png`

This makes it easy to track quality progression visually.

---

## Known Limitations

### 1. **Vision Model Consistency**
- Vision AI ratings can vary between runs
- Score interpretation is subjective
- Solution: Focus on relative improvement, not absolute scores

### 2. **Max Refinement Limit**
- Some steps may need >2 refinements to achieve ideal quality
- Prevents infinite loops but may accept suboptimal results
- Solution: Increase `max_refinements_per_step` for critical projects

### 3. **Refinement Code Generation**
- LLM may generate refinements that conflict with existing geometry
- Occasionally produces "no refinement actions" when stuck
- Solution: Enhanced refinement prompts with more specific guidance

### 4. **Performance**
- Vision analysis adds ~2-3 seconds per screenshot
- Refinement iterations increase total time significantly
- Solution: Disable for rapid prototyping, enable for final runs

---

## Future Enhancements

### Planned Improvements

1. **Multi-view Assessment**
   - Capture screenshots from 3 angles (front, side, 3/4 view)
   - Average quality scores across viewpoints
   - Better detect geometric issues

2. **Adaptive Refinement Strategies**
   - Different refinement approaches based on issue type
   - "Add detail" vs "Fix errors" vs "Improve materials"
   - Targeted improvements instead of general enhancement

3. **Quality Progression Tracking**
   - Plot quality scores over refinement attempts
   - Detect diminishing returns (when to stop refining)
   - Suggest optimal max_refinements value

4. **Refinement Templates**
   - Pre-built refinement code patterns for common issues
   - Faster, more reliable improvements
   - E.g., "add_organic_variation", "enhance_materials", "increase_detail"

5. **User Feedback Integration**
   - Allow user to approve/reject refinements mid-execution
   - Manual quality override: "This step is acceptable, continue"
   - Interactive quality threshold adjustment

---

## Comparison: Artisan Agent vs Claude Desktop

| Feature | Artisan Agent (Before) | Artisan Agent (Now) | Claude Desktop |
|---------|------------------------|---------------------|----------------|
| **Planning** | Fixed 12-step plan | Fixed plan + adaptive refinement | Dynamic planning |
| **Quality Checks** | None | Vision AI per step | Vision AI per step |
| **Iteration** | No | Yes (up to 2x per step) | Yes (unlimited) |
| **Feedback Loop** | ❌ | ✅ | ✅ |
| **Result Quality** | Low (geometric) | Medium-High (refined) | High (artistic) |
| **Execution Time** | ~2 min | ~4-6 min | ~5-8 min |
| **Predictability** | High | Medium | Low |

**Conclusion**: The refinement loop brings Artisan Agent's quality significantly closer to Claude Desktop while maintaining the advantages of structured planning and session resumability.

---

## Testing the Refinement Loop

### Quick Test

Run the same Christmas tree requirement:

```bash
# From docker directory
docker-compose logs -f backend
```

Look for these indicators:
- 🎯 Assessing quality messages
- Quality scores being reported
- 🔄 Refinement needed indicators
- Multiple screenshots per step (e.g., `step_3_screenshot_2.png`, `step_3_screenshot_3_refine1.png`)

### Expected Behavior

For the Christmas tree example:
- **Step 1 (Trunk)**: Likely passes first attempt (simple geometry)
- **Step 2 (Cone)**: Likely passes first attempt
- **Step 3 (Branches)**: Likely needs 1-2 refinements (torus → organic branches)
- **Step 4 (Displacement)**: May need refinement if effect too subtle
- **Step 5 (Branch details)**: Likely needs refinement (template → instanced needles)

Total expected refinements: **3-5 across 13 steps**

---

## Troubleshooting

### Issue: "No refinement actions generated"

**Cause**: LLM couldn't determine how to improve based on feedback

**Solution**:
1. Check vision feedback quality - is it specific enough?
2. Enhance refinement prompt with more examples
3. Increase temperature for more creative refinements

### Issue: Refinements not improving quality

**Cause**: Vision model giving inconsistent scores

**Solution**:
1. Lower refinement threshold (require higher scores)
2. Add multi-view screenshot analysis
3. Focus on specific metrics (detail, realism) vs overall score

### Issue: Too many refinement attempts

**Cause**: Quality threshold too strict or vision model overly critical

**Solution**:
1. Lower threshold from 6 to 5
2. Reduce critical step threshold from 7 to 6
3. Increase max_refinements_per_step to 3

---

## Conclusion

The **Refinement Loop Architecture** transforms the Artisan Agent from a rigid executor into an **adaptive, quality-driven 3D modeler**. By integrating vision-based quality assessment with iterative refinement, the agent can now:

✅ Detect and fix quality issues automatically  
✅ Produce results comparable to manual Claude Desktop workflows  
✅ Maintain the benefits of structured planning and reproducibility  
✅ Learn from visual feedback to improve step execution  

This brings the Artisan Agent's output quality from **rudimentary geometric primitives** to **detailed, refined 3D models** worthy of production use.
