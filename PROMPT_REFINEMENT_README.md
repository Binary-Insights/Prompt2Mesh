# Prompt Refinement Agent for 3D Modeling

This agent uses **LangChain**, **LangGraph**, and **LangSmith** with **Claude Sonnet 4.5** to transform simple user prompts into comprehensive, detailed 3D modeling descriptions for Blender.

## 🎯 Purpose

Users often provide brief prompts like "create a Christmas tree" but 3D modeling requires extensive details about:
- Exact dimensions and measurements
- Materials and textures
- Component structure
- Lighting and rendering properties
- Surface details and imperfections

The Prompt Refinement Agent fills this gap by:
1. **Analyzing** the user's prompt
2. **Assessing** if it contains enough detail
3. **Expanding** simple prompts with comprehensive specifications
4. **Refining** the description for clarity and completeness

## 🏗️ Architecture

### LangGraph Workflow

```
┌─────────────────┐
│ Analyze Prompt  │  - Extract key object
│                 │  - Identify mentioned details
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Assess Detail   │  - Check if prompt is detailed enough
│ Level           │  - Decide: expand or finalize
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────────────────┐
│Final │  │ Generate Details │  - Create comprehensive description
│Output│  │                  │  - Include all 7 key sections
└──────┘  └────────┬─────────┘
              │
              ▼
         ┌──────────────┐
         │ Refine       │  - Polish description
         │ Description  │  - Ensure consistency
         └──────┬───────┘
                │
                ▼
         ┌──────────────┐
         │ Final Output │
         └──────────────┘
```

### Key Components

1. **State Management** (TypedDict)
   - Tracks messages, reasoning steps, refinement status
   - Maintains conversation context

2. **Multi-Step Reasoning**
   - Analysis → Assessment → Generation → Refinement
   - Each step logged for transparency

3. **Claude Sonnet 4.5**
   - Advanced reasoning capabilities
   - Detailed technical knowledge
   - Structured output generation

4. **LangSmith Integration**
   - Automatic tracing enabled via environment variables
   - Monitor reasoning steps and performance

## 📦 Installation

1. **Install dependencies:**
```bash
pip install -e .
```

This installs:
- `langchain>=0.3.0`
- `langchain-anthropic>=0.3.0`
- `langchain-core>=0.3.0`
- `langgraph>=0.2.0`
- `langsmith>=0.2.0`
- `python-dotenv>=1.0.0`

2. **Configure environment variables:**

Your `.env` already contains:
```env
ANTHROPIC_API_KEY=sk-ant-api03-...
CLAUDE_MODEL=claude-sonnet-4-5-20250929
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_...
LANGCHAIN_PROJECT=ReAct-LangGraph-Function-Call
LANGSMITH_API_KEY=lsv2_pt_...
```

## 🚀 Usage

### Standalone Agent

```python
from prompt_refinement_agent import PromptRefinementAgent

# Initialize agent
agent = PromptRefinementAgent()

# Refine a simple prompt
result = agent.refine_prompt("Could you model a christmas tree")

print(result["refined_prompt"])
# Outputs comprehensive description with:
# - Overall Structure and Shape
# - Branch Architecture
# - Needles and Foliage
# - Lights, Ornaments, Garland
# - Materials and Lighting Considerations
```

### Run the Example

```bash
python prompt_refinement_agent.py
```

This demonstrates:
- Example 1: Simple prompt ("christmas tree") → expanded
- Example 2: Detailed prompt → formatted nicely

### Integrated with Streamlit

```bash
streamlit run src/frontend/streamlit_blender_chat_with_refinement.py
```

Features:
- Toggle to enable/disable prompt refinement
- Shows reasoning steps in UI
- Indicates when prompts were expanded
- Seamlessly integrates with Blender agent

## 📊 Output Structure

The agent returns:

```python
{
    "refined_prompt": str,        # Comprehensive description
    "reasoning_steps": list[str], # Analysis, assessment, generation steps
    "is_detailed": bool,          # Was original prompt detailed?
    "original_prompt": str        # User's original input
}
```

### Refined Prompt Sections

Every expanded prompt includes:

1. **Overall Structure and Shape**
   - Dimensions (height, width, depth)
   - Basic geometric form
   - Proportions and scale

2. **Components and Parts**
   - Major components list
   - Sub-components
   - Connection methods

3. **Materials and Textures**
   - Material types
   - Surface textures
   - Color specifications
   - Reflectivity

4. **Fine Details**
   - Decorative elements
   - Patterns and engravings
   - Hardware details

5. **Measurements and Specifications**
   - Precise measurements
   - Material thickness
   - Spacing and angles

6. **Lighting and Rendering Considerations**
   - Light interaction
   - Subsurface scattering
   - Emission properties

7. **Variations and Imperfections**
   - Natural variations
   - Asymmetries
   - Random elements

## 🧠 How It Works

### 1. Analysis Phase
```python
"You are an expert 3D modeling analyst..."
# Extracts primary object, specific details, complexity
```

### 2. Assessment Phase
```python
# Checks for: dimensions, materials, textures, colors,
# structure, lighting considerations
# Returns: "DETAILED" or "NEEDS_EXPANSION"
```

### 3. Generation Phase (if needed)
```python
"You are a 3D modeling expert who creates exhaustive descriptions..."
# Generates 7-section comprehensive description
# Uses technical terminology and specific measurements
```

### 4. Refinement Phase
```python
# Ensures completeness, consistency, clarity
# Enhances while maintaining comprehensiveness
```

## 🔍 LangSmith Monitoring

With `LANGCHAIN_TRACING_V2=true`, all runs are automatically tracked:

1. Visit: https://smith.langchain.com
2. View your project: "ReAct-LangGraph-Function-Call"
3. See traces for:
   - Each node execution
   - LLM calls and responses
   - Token usage
   - Latency metrics

## 🎨 Example Transformation

**Input:**
```
"Could you model a christmas tree"
```

**Output:**
```markdown
## Overall Structure and Shape
A typical Christmas tree has a conical silhouette, widest at the base 
and tapering to a pointed top. The tree usually stands 6-8 feet tall 
for indoor displays...

## Branch Architecture
The branches radiate outward from the trunk in a spiral pattern, with 
each tier separated by 6-12 inches vertically...

[... continues with comprehensive details ...]
```

## 🔧 Customization

### Adjust Temperature
```python
self.llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0.7,  # Higher = more creative
    # temperature=0.3  # Lower = more focused
)
```

### Modify System Prompts

Edit the prompts in:
- `_analyze_prompt_node`
- `_assess_detail_level_node`
- `_generate_details_node`
- `_refine_description_node`

### Add Custom Sections

Extend the detail generation prompt to include additional sections specific to your modeling needs.

## 📝 Integration Notes

### With Blender Agent

The refined prompt is sent to the Blender agent instead of the original:

```python
if use_refinement:
    refinement_result = refinement_agent.refine_prompt(prompt)
    refined_prompt = refinement_result["refined_prompt"]
    
# Send refined_prompt to Blender agent
response = client.chat(refined_prompt)
```

### Thread Management

Each conversation has a unique `thread_id`:
```python
result = agent.refine_prompt(
    user_prompt="...",
    thread_id="user_session_123"  # Maintains context
)
```

## 🎯 Benefits

1. **Consistency**: Every prompt gets standardized, comprehensive details
2. **Quality**: AI ensures no important details are missed
3. **Efficiency**: Users don't need 3D modeling expertise to describe objects
4. **Traceability**: LangSmith tracks every reasoning step
5. **Flexibility**: Works with both simple and complex prompts

## 🚦 Status Indicators

The agent provides visual feedback:
- 🔍 Analyzing user prompt...
- 📊 Assessing detail level...
- 🎨 Generating comprehensive details...
- ✨ Refining description...
- 📝 Preparing final output...
- ✅ Refinement Complete

## 📚 Further Reading

- [LangChain Documentation](https://python.langchain.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [Anthropic Claude](https://www.anthropic.com/claude)

---

**Author**: Built with Claude Sonnet 4.5, LangChain, and LangGraph
**License**: MIT
