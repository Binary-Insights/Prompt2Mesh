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

# Load environment variables
load_dotenv()

# Global agent instance
agent: BlenderChatAgent = None


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
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
            "clear_history": "/clear-history"
        }
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
        result = await agent.chat(request.message)
        
        return ChatResponse(
            responses=result["responses"],
            tool_calls=result["tool_calls"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during chat: {str(e)}"
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


if __name__ == "__main__":
    import uvicorn
    
    # Run the server
    uvicorn.run(
        "backend_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
