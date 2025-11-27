"""
Prompt Refinement Agent for 3D Modeling in Blender
Uses LangGraph for reasoning and LangChain for LLM integration
Expands simple prompts into comprehensive 3D modeling descriptions
"""

import os
from typing import TypedDict, Annotated, Sequence
from dotenv import load_dotenv

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langsmith import traceable
from langsmith import Client

from langgraph.graph import StateGraph, END
# from langgraph.prebuilt import ToolExecutor
from langgraph.checkpoint.memory import MemorySaver

# Load environment variables
load_dotenv()

# Configure LangSmith for async/background tracing
os.environ["LANGCHAIN_CALLBACKS_BACKGROUND"] = "true"

# Initialize LangSmith client for manual logging
langsmith_client = Client()


class AgentState(TypedDict):
    """State of the prompt refinement agent"""
    messages: Annotated[Sequence[BaseMessage], "The messages in the conversation"]
    user_prompt: str
    reasoning_steps: list[str]
    refined_prompt: str
    is_detailed: bool
    iteration_count: int


class PromptRefinementAgent:
    """
    Agent that analyzes user prompts and expands them into detailed 3D modeling descriptions.
    
    The agent uses a multi-step reasoning process:
    1. Analyze the user's prompt for completeness
    2. Identify missing details needed for 3D modeling
    3. Research and expand on missing information
    4. Generate comprehensive description with specific measurements, materials, textures, etc.
    """
    
    def __init__(self):
        """Initialize the prompt refinement agent"""
        # Initialize Claude Sonnet 4.5
        self.llm = ChatAnthropic(
            model=os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5-20250929"),
            temperature=0.7,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )
        
        # Memory for conversation history (initialize before graph)
        self.memory = MemorySaver()
        
        # Create the graph
        self.graph = self._create_graph()
    
    def _create_graph(self) -> StateGraph:
        """Create the LangGraph workflow for prompt refinement"""
        
        # Define the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("analyze_prompt", self._analyze_prompt_node)
        workflow.add_node("assess_detail_level", self._assess_detail_level_node)
        workflow.add_node("generate_details", self._generate_details_node)
        workflow.add_node("refine_description", self._refine_description_node)
        workflow.add_node("final_output", self._final_output_node)
        
        # Set entry point
        workflow.set_entry_point("analyze_prompt")
        
        # Add edges
        workflow.add_edge("analyze_prompt", "assess_detail_level")
        
        # Conditional edge: if detailed enough, skip to final output
        workflow.add_conditional_edges(
            "assess_detail_level",
            self._should_expand_prompt,
            {
                "expand": "generate_details",
                "finalize": "final_output"
            }
        )
        
        workflow.add_edge("generate_details", "refine_description")
        workflow.add_edge("refine_description", "final_output")
        workflow.add_edge("final_output", END)
        
        return workflow.compile(checkpointer=self.memory)
    
    @traceable(name="analyze_prompt")
    def _analyze_prompt_node(self, state: AgentState) -> AgentState:
        """Analyze the user's prompt to understand what they want to model"""
        print("\n🔍 Analyzing user prompt...")
        
        analysis_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert 3D modeling analyst. Your job is to analyze user requests 
            for 3D models and identify the key object they want to create.
            
            Extract:
            1. The primary object to model
            2. Any specific details mentioned
            3. The overall complexity of the request
            
            Be concise and factual."""),
            ("human", "{user_prompt}")
        ])
        
        chain = analysis_prompt | self.llm | StrOutputParser()
        analysis = chain.invoke({"user_prompt": state["user_prompt"]})
        
        state["reasoning_steps"].append(f"Analysis: {analysis}")
        state["messages"].append(AIMessage(content=f"Analysis: {analysis}"))
        
        print(f"✅ Analysis complete")
        return state
    
    @traceable(name="assess_detail_level")
    def _assess_detail_level_node(self, state: AgentState) -> AgentState:
        """Assess if the prompt has enough detail for 3D modeling"""
        print("\n📊 Assessing detail level...")
        
        assessment_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a STRICT evaluator for 3D modeling prompts in Blender.
            
            A prompt is ONLY "DETAILED" if it contains AT LEAST 4 of these 6 elements:
            1. Specific dimensions/sizes (e.g., "6 feet tall", "2 meters wide")
            2. Material descriptions (e.g., "oak wood", "brushed aluminum")
            3. Texture details (e.g., "rough surface", "glossy finish")
            4. Color specifications (e.g., "dark green", "RGB(120,80,40)")
            5. Structural components listed (e.g., "4 legs", "curved backrest")
            6. Surface features/details (e.g., "carved patterns", "metal hinges")
            
            If the prompt is just a simple object name or basic description (like "a chair", "model a tree", 
            "create a table"), it is NOT detailed enough and should be marked as "NEEDS_EXPANSION".
            
            Be STRICT. Most simple user prompts should be expanded.
            
            Respond with ONLY "DETAILED" or "NEEDS_EXPANSION" followed by a count of how many criteria are met."""),
            ("human", "User prompt: {user_prompt}\n\nAnalysis: {analysis}")
        ])
        
        chain = assessment_prompt | self.llm | StrOutputParser()
        assessment = chain.invoke({
            "user_prompt": state["user_prompt"],
            "analysis": state["reasoning_steps"][-1]
        })
        
        # More robust parsing: only DETAILED if it starts with "DETAILED"
        assessment_upper = assessment.upper().strip()
        state["is_detailed"] = assessment_upper.startswith("DETAILED")
        
        state["reasoning_steps"].append(f"Assessment: {assessment}")
        state["messages"].append(AIMessage(content=f"Detail Assessment: {assessment}"))
        
        print(f"✅ Detail level: {'Sufficient' if state['is_detailed'] else 'Needs expansion'}")
        print(f"   Assessment: {assessment}")
        print(f"   is_detailed flag: {state['is_detailed']}")
        return state
    
    @traceable(name="should_expand_prompt_decision")
    def _should_expand_prompt(self, state: AgentState) -> str:
        """Decide whether to expand the prompt or finalize"""
        if state["is_detailed"]:
            return "finalize"
        return "expand"
    
    @traceable(name="generate_details")
    def _generate_details_node(self, state: AgentState) -> AgentState:
        """Generate comprehensive details for the 3D model"""
        print("\n🎨 Generating comprehensive details...")
        
        detail_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a 3D modeling expert who creates exhaustive, detailed descriptions 
            for modeling objects in Blender. Your descriptions should be so comprehensive that a 3D artist 
            could create an accurate model without any additional reference.
            
            For EVERY object, provide:
            
            1. **Overall Structure and Shape**
               - Exact dimensions (height, width, depth) in feet/inches or meters
               - Basic geometric form and silhouette
               - Proportions and scale relationships
               - Base/foundation details
            
            2. **Components and Parts**
               - List all major components
               - Sub-components for each major part
               - How parts connect/attach to each other
               - Hierarchy and structure
            
            3. **Materials and Textures**
               - Specific material types (wood, metal, plastic, fabric, etc.)
               - Surface texture descriptions (smooth, rough, glossy, matte)
               - Color specifications (exact shades when possible)
               - Reflectivity and specularity
            
            4. **Fine Details**
               - Decorative elements
               - Patterns, engravings, or surface features
               - Hardware (screws, bolts, hinges, etc.)
               - Wear, age, or weathering effects
            
            5. **Measurements and Specifications**
               - Precise measurements for key features
               - Thickness of materials
               - Spacing between elements
               - Angles and curves
            
            6. **Lighting and Rendering Considerations**
               - How light interacts with surfaces
               - Subsurface scattering needs
               - Emission properties for light sources
               - Shadow behavior
            
            7. **Variations and Imperfections**
               - Natural variations in the object
               - Asymmetries that add realism
               - Random elements (if applicable)
            
            Use specific measurements, technical terminology, and vivid descriptions. Think like you're 
            writing technical documentation for a 3D modeling project.
            
            Format your response with clear section headers using markdown (##)."""),
            ("human", """Create a comprehensive 3D modeling description for: {user_prompt}
            
            Previous analysis: {analysis}""")
        ])
        
        chain = detail_prompt | self.llm | StrOutputParser()
        details = chain.invoke({
            "user_prompt": state["user_prompt"],
            "analysis": "\n".join(state["reasoning_steps"])
        })
        
        state["refined_prompt"] = details
        state["reasoning_steps"].append("Generated comprehensive details")
        state["messages"].append(AIMessage(content=details))
        
        print(f"✅ Generated {len(details)} characters of detailed description")
        return state
    
    @traceable(name="refine_description")
    def _refine_description_node(self, state: AgentState) -> AgentState:
        """Refine and polish the generated description"""
        print("\n✨ Refining description...")
        
        refinement_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are reviewing and polishing a 3D modeling description. 
            
            Your tasks:
            1. Ensure all sections are complete and well-organized
            2. Verify measurements are consistent and realistic
            3. Add any missing technical details
            4. Ensure the description flows logically
            5. Maintain the comprehensive nature while improving clarity
            
            Keep the same section structure but enhance the content quality."""),
            ("human", """Refine this 3D modeling description:
            
            {description}
            
            Original request: {user_prompt}""")
        ])
        
        chain = refinement_prompt | self.llm | StrOutputParser()
        refined = chain.invoke({
            "description": state["refined_prompt"],
            "user_prompt": state["user_prompt"]
        })
        
        state["refined_prompt"] = refined
        state["reasoning_steps"].append("Refined and polished description")
        state["messages"].append(AIMessage(content="Description refined"))
        
        print(f"✅ Refinement complete")
        return state
    
    @traceable(name="final_output")
    def _final_output_node(self, state: AgentState) -> AgentState:
        """Prepare the final output"""
        print("\n📝 Preparing final output...")
        
        if state["is_detailed"]:
            # User provided enough detail, just format it nicely
            final_prompt = ChatPromptTemplate.from_messages([
                ("system", """The user has provided a detailed description. Format it nicely 
                and ensure it's ready for 3D modeling. Add section headers if missing."""),
                ("human", "{user_prompt}")
            ])
            
            chain = final_prompt | self.llm | StrOutputParser()
            final_output = chain.invoke({"user_prompt": state["user_prompt"]})
            state["refined_prompt"] = final_output
        
        # If refined_prompt is empty, use user_prompt
        if not state["refined_prompt"]:
            state["refined_prompt"] = state["user_prompt"]
        
        print(f"✅ Final output ready ({len(state['refined_prompt'])} characters)")
        return state
    
    @traceable(name="prompt_refinement_agent", run_type="chain")
    def refine_prompt(self, user_prompt: str, thread_id: str = "default") -> dict:
        """
        Refine a user's prompt into a comprehensive 3D modeling description.
        
        Args:
            user_prompt: The user's input describing what they want to model
            thread_id: Unique identifier for the conversation thread
            
        Returns:
            Dictionary containing:
            - refined_prompt: The comprehensive description
            - reasoning_steps: Steps taken during refinement
            - is_detailed: Whether the original was already detailed
        """
        print(f"\n{'='*60}")
        print(f"🚀 Starting Prompt Refinement")
        print(f"{'='*60}")
        print(f"\n📥 User Input: {user_prompt}")
        
        # Initialize state
        initial_state = {
            "messages": [HumanMessage(content=user_prompt)],
            "user_prompt": user_prompt,
            "reasoning_steps": [],
            "refined_prompt": "",
            "is_detailed": False,
            "iteration_count": 0
        }
        
        # Run the graph
        config = {"configurable": {"thread_id": thread_id}}
        final_state = self.graph.invoke(initial_state, config)
        
        print(f"\n{'='*60}")
        print(f"✅ Refinement Complete")
        print(f"{'='*60}\n")
        
        return {
            "refined_prompt": final_state["refined_prompt"],
            "reasoning_steps": final_state["reasoning_steps"],
            "is_detailed": final_state["is_detailed"],
            "original_prompt": user_prompt
        }
    
    async def arefine_prompt(self, user_prompt: str, thread_id: str = "default") -> dict:
        """Async version of refine_prompt"""
        # For now, call the sync version
        # TODO: Implement fully async version if needed
        return self.refine_prompt(user_prompt, thread_id)


def main():
    """Example usage of the Prompt Refinement Agent"""
    agent = PromptRefinementAgent()
    
    # Example 1: Simple prompt
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Christmas Tree Request")
    print("="*80)
    
    result1 = agent.refine_prompt("Could you model a christmas tree")
    
    print("\n📤 FINAL OUTPUT:")
    print("-" * 80)
    print(result1["refined_prompt"])
    print("-" * 80)
    
    print("\n🧠 REASONING STEPS:")
    for i, step in enumerate(result1["reasoning_steps"], 1):
        print(f"{i}. {step}")
    
    # Example 2: Already detailed prompt
    print("\n" + "="*80)
    print("EXAMPLE 2: Detailed Request")
    print("="*80)
    
    # detailed_prompt = """Create a realistic wooden dining chair with the following specifications:
    # - Seat height: 18 inches from ground
    # - Back height: 36 inches total
    # - Seat dimensions: 16x16 inches
    # - Oak wood with medium brown stain
    # - Curved backrest with vertical slats
    # - Slightly tapered legs"""
    
    # result2 = agent.refine_prompt(detailed_prompt)
    
    # print("\n📤 FINAL OUTPUT:")
    # print("-" * 80)
    # print(result2["refined_prompt"])
    # print("-" * 80)
    
    # print(f"\nOriginal was detailed: {result2['is_detailed']}")


if __name__ == "__main__":
    main()
