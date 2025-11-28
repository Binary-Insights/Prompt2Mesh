"""
FastAPI Backend Server for Blender Chat
Provides REST API endpoints for the Streamlit frontend
"""
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional
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
from src.artisan_agent import ArtisanAgent
from src.login import AuthService, init_db

# Load environment variables
load_dotenv()

# Global agent instances
agent: BlenderChatAgent = None
refinement_agent: PromptRefinementAgent = None
artisan_agent: ArtisanAgent = None
artisan_tasks: Dict[str, Dict[str, Any]] = {}  # Track running tasks
auth_service: AuthService = None


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
    error: Optional[str] = None


class RefinePromptRequest(BaseModel):
    """Request model for prompt refinement endpoint"""
    prompt: str
    thread_id: str = "default"
    detail_level: str = "comprehensive"  # Options: concise, moderate, comprehensive


class RefinePromptResponse(BaseModel):
    """Response model for prompt refinement endpoint"""
    refined_prompt: str
    reasoning_steps: List[str]
    is_detailed: bool
    original_prompt: str


class ArtisanModelingRequest(BaseModel):
    """Request model for artisan modeling endpoint"""
    requirement_file: str  # Path to JSON requirement file
    use_resume: bool = True


class ArtisanModelingResponse(BaseModel):
    """Response model for artisan modeling endpoint"""
    task_id: str
    status: str  # "started", "running", "completed", "failed"
    message: str


class ArtisanTaskStatus(BaseModel):
    """Response model for task status"""
    task_id: str
    status: str
    session_id: Optional[str] = None
    steps_executed: int = 0
    screenshots_captured: int = 0
    screenshot_directory: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    tool_results: List[Dict[str, Any]] = []


class LoginRequest(BaseModel):
    """Request model for login endpoint"""
    username: str
    password: str


class LoginResponse(BaseModel):
    """Response model for login endpoint"""
    success: bool
    token: Optional[str] = None
    user_id: Optional[int] = None
    username: Optional[str] = None
    expires_at: Optional[str] = None
    message: str


class VerifyTokenRequest(BaseModel):
    """Request model for token verification"""
    token: str


class VerifyTokenResponse(BaseModel):
    """Response model for token verification"""
    valid: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    message: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    # Startup
    global refinement_agent, auth_service
    
    # Initialize authentication service
    try:
        print("🔐 Initializing authentication service...")
        init_db()  # Create database tables
        auth_service = AuthService()
        print("✅ Authentication service initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize Authentication Service: {e}")
        auth_service = None
    
    # Initialize refinement agent
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
        "version": "1.1.0",
        "endpoints": {
            "auth": {
                "login": "/auth/login",
                "verify": "/auth/verify",
                "logout": "/auth/logout"
            },
            "blender": {
                "connect": "/connect",
                "disconnect": "/disconnect",
                "chat": "/chat",
                "status": "/status",
                "history": "/history",
                "clear_history": "/clear-history"
            },
            "refinement": {
                "refine_prompt": "/refine-prompt"
            },
            "artisan": {
                "model": "/artisan/model",
                "status": "/artisan/status/{task_id}",
                "tasks": "/artisan/tasks"
            }
        },
        "auth_available": auth_service is not None,
        "refinement_agent_available": refinement_agent is not None,
        "artisan_agent_available": artisan_agent is not None
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
        # print(f"\n=== User Message ===\n{request.message}\n==================\n")
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
            thread_id=request.thread_id,
            detail_level=request.detail_level
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


@app.post("/artisan/model", response_model=ArtisanModelingResponse)
async def start_artisan_modeling(request: ArtisanModelingRequest):
    """Start an Artisan Agent modeling task"""
    global artisan_agent, artisan_tasks
    
    # Validate requirement file exists
    req_file = Path(request.requirement_file)
    if not req_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Requirement file not found: {request.requirement_file}"
        )
    
    try:
        # Generate task ID
        import uuid
        task_id = str(uuid.uuid4())[:8]
        
        # Create new artisan agent instance for this task
        task_agent = ArtisanAgent()
        
        # Store task info
        artisan_tasks[task_id] = {
            "status": "initializing",
            "agent": task_agent,
            "requirement_file": request.requirement_file,
            "use_resume": request.use_resume,
            "result": None,
            "error": None
        }
        
        # Start task in background
        asyncio.create_task(_run_artisan_task(task_id))
        
        return ArtisanModelingResponse(
            task_id=task_id,
            status="started",
            message=f"Modeling task started with ID: {task_id}"
        )
        
    except Exception as e:
        import traceback
        error_detail = f"Error starting artisan task: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def _run_artisan_task(task_id: str):
    """Background task runner for artisan modeling"""
    global artisan_tasks
    
    task_info = artisan_tasks[task_id]
    agent = task_info["agent"]
    
    try:
        # Update status
        task_info["status"] = "running"
        
        # Initialize agent
        print(f"[Task {task_id}] Initializing Artisan Agent...")
        await agent.initialize()
        
        # Run modeling task
        print(f"[Task {task_id}] Running modeling task: {task_info['requirement_file']}")
        result = await agent.run(
            task_info["requirement_file"],
            use_deterministic_session=task_info["use_resume"]
        )
        
        # Store result
        task_info["result"] = result
        task_info["status"] = "completed"
        print(f"[Task {task_id}] Completed successfully")
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        task_info["error"] = str(e)
        task_info["status"] = "failed"
        print(f"[Task {task_id}] Failed: {error_msg}")
        
    finally:
        # Cleanup agent
        try:
            await agent.cleanup()
        except Exception:
            pass


@app.get("/artisan/status/{task_id}", response_model=ArtisanTaskStatus)
async def get_artisan_task_status(task_id: str):
    """Get the status of an artisan modeling task"""
    global artisan_tasks
    
    if task_id not in artisan_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_info = artisan_tasks[task_id]
    result = task_info.get("result")
    
    # Build response
    response = ArtisanTaskStatus(
        task_id=task_id,
        status=task_info["status"],
        error=task_info.get("error")
    )
    
    # Add result details if available
    if result:
        response.session_id = result.get("session_id")
        response.steps_executed = result.get("steps_executed", 0)
        response.screenshots_captured = result.get("screenshots_captured", 0)
        response.screenshot_directory = result.get("screenshot_directory")
        response.success = result.get("success", False)
        response.tool_results = result.get("tool_results", [])
    
    return response


@app.get("/artisan/tasks")
async def list_artisan_tasks():
    """List all artisan modeling tasks"""
    global artisan_tasks
    
    tasks_summary = []
    for task_id, info in artisan_tasks.items():
        tasks_summary.append({
            "task_id": task_id,
            "status": info["status"],
            "requirement_file": info["requirement_file"],
            "use_resume": info["use_resume"]
        })
    
    return {
        "tasks": tasks_summary,
        "total": len(tasks_summary)
    }


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    global auth_service
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        result = auth_service.authenticate_user(request.username, request.password)
        
        if result:
            return LoginResponse(
                success=True,
                token=result["token"],
                user_id=result["user_id"],
                username=result["username"],
                expires_at=result["expires_at"],
                message="Login successful"
            )
        else:
            return LoginResponse(
                success=False,
                message="Invalid username or password"
            )
    
    except Exception as e:
        import traceback
        error_detail = f"Error during login: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/auth/verify", response_model=VerifyTokenResponse)
async def verify_token(request: VerifyTokenRequest):
    """Verify JWT token validity"""
    global auth_service
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        payload = auth_service.verify_token(request.token)
        
        if payload:
            return VerifyTokenResponse(
                valid=True,
                user_id=payload.get("user_id"),
                username=payload.get("username"),
                message="Token is valid"
            )
        else:
            return VerifyTokenResponse(
                valid=False,
                message="Invalid or expired token"
            )
    
    except Exception as e:
        import traceback
        error_detail = f"Error during token verification: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/auth/logout")
async def logout(request: VerifyTokenRequest):
    """Logout user by invalidating token"""
    global auth_service
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        auth_service.logout(request.token)
        return {"success": True, "message": "Logged out successfully"}
    
    except Exception as e:
        import traceback
        error_detail = f"Error during logout: {str(e)}\n{traceback.format_exc()}"
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
