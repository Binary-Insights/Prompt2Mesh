"""
FastAPI Backend Server for Blender Chat
Provides REST API endpoints for the Streamlit frontend
"""
import os
import sys
import asyncio
from typing import Dict, Any, List
from contextlib import asynccontextmanager
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from src.blender.blender_agent import BlenderChatAgent
from src.refinement_agent import PromptRefinementAgent

# Load environment variables
load_dotenv()

# Global agent instances
agent: BlenderChatAgent = None
refinement_agent: PromptRefinementAgent = None


class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    responses: List[str]
    tool_calls: List[Dict[str, Any]]


class ConnectionStatus(BaseModel):
    """Response model for connection status"""
    connected: bool
    num_tools: int = 0
    error: str = None


class RefinePromptRequest(BaseModel):
    """Request model for prompt refinement endpoint"""
    prompt: str
    thread_id: str = "default"


class RefinePromptResponse(BaseModel):
    """Response model for prompt refinement endpoint"""
    refined_prompt: str
    reasoning_steps: List[str]
    is_detailed: bool
    original_prompt: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    global refinement_agent
    try:
        refinement_agent = PromptRefinementAgent()
        print("✅ Prompt Refinement Agent initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize Refinement Agent: {e}")
        refinement_agent = None
    
    yield
    
    # Shutdown
    global agent
    if agent:
        try:
            await agent.cleanup()
        except Exception:
            pass


# Initialize FastAPI app
app = FastAPI(
    title="Blender Chat API",
    description="REST API for AI-powered Blender control",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Blender Chat API",
        "version": "1.0.0",
        "endpoints": {
            "connect": "/connect",
            "disconnect": "/disconnect",
            "chat": "/chat",
            "status": "/status",
            "history": "/history",
            "clear_history": "/clear-history",
            "refine_prompt": "/refine-prompt"
        },
        "refinement_agent_available": refinement_agent is not None
    }


@app.post("/connect", response_model=ConnectionStatus)
async def connect():
    """Connect to Blender MCP server"""
    global agent, agent_loop
    
    # Check if already connected
    if agent and not agent._cleanup_done:
        return ConnectionStatus(
            connected=True,
            num_tools=len(agent.tools)
        )
    
    try:
        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ANTHROPIC_API_KEY not set in environment"
            )
        
        # Create new agent
        agent = BlenderChatAgent(api_key=api_key)
        
        # Initialize MCP connection using await (we're in an async function)
        num_tools = await agent.initialize_mcp()
        
        return ConnectionStatus(
            connected=True,
            num_tools=num_tools
        )
    
    except Exception as e:
        agent = None
        return ConnectionStatus(
            connected=False,
            error=str(e)
        )


@app.post("/disconnect")
async def disconnect():
    """Disconnect from Blender MCP server"""
    global agent
    
    if not agent:
        return {"status": "not_connected"}
    
    try:
        await agent.cleanup()
        
        agent = None
        
        return {"status": "disconnected"}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during disconnect: {str(e)}"
        )


@app.get("/status", response_model=ConnectionStatus)
async def get_status():
    """Get connection status"""
    global agent
    
    if agent and not agent._cleanup_done:
        return ConnectionStatus(
            connected=True,
            num_tools=len(agent.tools)
        )
    else:
        return ConnectionStatus(
            connected=False
        )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Send a message to the agent"""
    global agent
    
    if not agent or agent._cleanup_done:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not connected to Blender. Call /connect first."
        )
    
    try:
        print(f"\n=== User Message ===\n{request.message}\n==================\n")
        result = await agent.chat(request.message)
        
        return ChatResponse(
            responses=result["responses"],
            tool_calls=result["tool_calls"]
        )
    
    except Exception as e:
        import traceback
        error_detail = f"Error during chat: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)  # Log to console
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/history")
async def get_history():
    """Get conversation history"""
    global agent
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not connected to Blender"
        )
    
    return {
        "history": agent.get_conversation_history()
    }


@app.post("/clear-history")
async def clear_history():
    """Clear conversation history"""
    global agent
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not connected to Blender"
        )
    
    agent.clear_conversation_history()
    
    return {"status": "cleared"}


@app.post("/refine-prompt", response_model=RefinePromptResponse)
async def refine_prompt(request: RefinePromptRequest):
    """Refine a user prompt into a comprehensive 3D modeling description"""
    global refinement_agent
    
    if not refinement_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt refinement agent not available"
        )
    
    try:
        print(f"\n🧠 Refining prompt: {request.prompt[:100]}...")
        
        result = refinement_agent.refine_prompt(
            user_prompt=request.prompt,
            thread_id=request.thread_id
        )
        
        print(f"✅ Refinement complete: {len(result['refined_prompt'])} characters")
        
        return RefinePromptResponse(
            refined_prompt=result["refined_prompt"],
            reasoning_steps=result["reasoning_steps"],
            is_detailed=result["is_detailed"],
            original_prompt=result["original_prompt"]
        )
    
    except Exception as e:
        import traceback
        error_detail = f"Error during prompt refinement: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "backend_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
