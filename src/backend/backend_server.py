"""
FastAPI Backend Server for Blender Chat
Provides REST API endpoints for the Streamlit frontend
"""
import os
import sys
import asyncio
import time
from typing import Dict, Any, List, Optional
from contextlib import asynccontextmanager
from pathlib import Path
from datetime import datetime

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

# Conditional import based on deployment mode
DEPLOYMENT_MODE = os.getenv("DEPLOYMENT_MODE", "docker")  # "docker" or "kubernetes"

if DEPLOYMENT_MODE == "kubernetes":
    from src.backend.k8s_user_session_manager import K8sUserSessionManager as SessionManager
    print(f"🚀 Running in Kubernetes mode")
else:
    from src.backend.user_session_manager import UserSessionManager as SessionManager
    print(f"🐳 Running in Docker mode")

# Load environment variables
load_dotenv()

# Global agent instances
agent: BlenderChatAgent = None
refinement_agent: PromptRefinementAgent = None
artisan_agent: ArtisanAgent = None
artisan_tasks: Dict[str, Dict[str, Any]] = {}  # Track running tasks
refinement_jobs: Dict[str, Dict[str, Any]] = {}  # Track refinement background jobs
auth_service: AuthService = None
session_manager: SessionManager = None  # Per-user session manager (Docker or K8s)


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


class RefinePromptJobRequest(BaseModel):
    """Request model for async prompt refinement endpoint"""
    prompt: str
    detail_level: str = "comprehensive"


class RefinePromptJobResponse(BaseModel):
    """Response model for async prompt refinement job"""
    job_id: str
    status: str  # "pending", "processing", "completed", "failed"
    message: str


class RefinePromptJobStatus(BaseModel):
    """Response model for checking refinement job status"""
    job_id: str
    status: str
    refined_prompt: Optional[str] = None
    reasoning_steps: Optional[List[str]] = None
    is_detailed: Optional[bool] = None
    original_prompt: Optional[str] = None
    error: Optional[str] = None
    progress: Optional[str] = None


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
    messages: List[str] = []  # Add messages list
    progress: int = 0  # Add progress percentage


class SignupRequest(BaseModel):
    """Request model for signup endpoint"""
    username: str
    password: str


class SignupResponse(BaseModel):
    """Response model for signup endpoint"""
    success: bool
    user_id: Optional[int] = None
    username: Optional[str] = None
    message: str


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
    # Blender session info
    mcp_port: Optional[int] = None
    blender_ui_port: Optional[int] = None
    blender_ui_url: Optional[str] = None


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
    global refinement_agent, auth_service, session_manager
    
    # Initialize authentication service
    try:
        print("🔐 Initializing authentication service...")
        init_db()  # Create database tables
        auth_service = AuthService()
        print("✅ Authentication service initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize Authentication Service: {e}")
        auth_service = None
    
    # Initialize user session manager
    try:
        print(f"🔧 Initializing user session manager ({DEPLOYMENT_MODE} mode)...")
        if DEPLOYMENT_MODE == "kubernetes":
            namespace = os.getenv("K8S_NAMESPACE", "default")
            session_manager = SessionManager(namespace=namespace)
            print(f"✅ Kubernetes session manager initialized (namespace: {namespace})")
        else:
            session_manager = SessionManager()
            print("✅ Docker session manager initialized")
    except Exception as e:
        print(f"⚠️ Failed to initialize User Session Manager: {e}")
        import traceback
        traceback.print_exc()
        session_manager = None
    
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
    
    # Cleanup all user sessions
    if session_manager:
        print("🧹 Cleaning up user sessions...")
        for session in session_manager.list_active_sessions():
            try:
                session_manager.stop_user_session(session.user_id)
            except Exception as e:
                print(f"Error cleaning up session for {session.username}: {e}")


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
async def connect(user_id: int = None):
    """Connect to Blender MCP server for a specific user"""
    global agent, agent_loop
    
    # If no user_id provided, try to use the shared Blender instance (backward compatibility)
    if not user_id:
        # Try connecting to default Blender instance on port 9876
        if not agent:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ANTHROPIC_API_KEY not set in environment"
                )
            agent = BlenderChatAgent(api_key=api_key, mcp_host="localhost", mcp_port=9876)
            try:
                num_tools = await agent.initialize_mcp()
                return ConnectionStatus(connected=True, num_tools=num_tools)
            except Exception as e:
                await agent.cleanup()
                agent = None
                return ConnectionStatus(connected=False, error=str(e))
        return ConnectionStatus(connected=True, num_tools=len(agent.tools))
    
    # Get user's session to find their Blender port
    if not session_manager:
        return ConnectionStatus(
            connected=False,
            error="Session manager not available. Please restart backend."
        )
    
    user_session = session_manager.get_user_session(user_id)
    if not user_session:
        return ConnectionStatus(
            connected=False,
            error="No active Blender session. Please login again."
        )
    
    # Check if already connected
    if agent and not agent._cleanup_done:
        # Test if Blender is actually reachable
        try:
            test_result = await agent.call_mcp_tool("get_scene_info", {})
            # Check both the success flag and result content for errors
            result_str = str(test_result.get("result", "")).lower()
            if (not test_result.get("success", False) or 
                "unknown tool" in result_str or
                "connection refused" in result_str or 
                "could not connect" in result_str or
                "error executing" in result_str or
                "failed to connect" in result_str):
                # Connection is broken, clean up
                await agent.cleanup()
                agent = None
                return ConnectionStatus(
                    connected=False,
                    error="Blender MCP addon is not running. Please enable the addon in Blender."
                )
            return ConnectionStatus(
                connected=True,
                num_tools=len(agent.tools)
            )
        except Exception:
            # Connection test failed, clean up
            await agent.cleanup()
            agent = None
            return ConnectionStatus(
                connected=False,
                error="Blender MCP addon is not running. Please enable the addon in Blender."
            )
    
    try:
        # Check for API key
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ANTHROPIC_API_KEY not set in environment"
            )
        
        # Create new agent with user-specific MCP connection
        if DEPLOYMENT_MODE == "kubernetes":
            # In Kubernetes, use service DNS name
            mcp_host = f"{user_session.service_name}.{user_session.namespace}.svc.cluster.local"
            print(f"🔌 Connecting to user's Blender pod via service: {mcp_host}:9876")
        else:
            # In Docker, use container name
            mcp_host = user_session.container_name
            print(f"🔌 Connecting to user's Blender container: {mcp_host}:9876")
        
        print(f"   User: {user_session.username} (ID: {user_session.user_id})")
        print(f"   MCP Port (internal): 9876")
        if hasattr(user_session, 'mcp_port'):
            print(f"   MCP Port (external): {user_session.mcp_port}")
        if hasattr(user_session, 'blender_ui_port'):
            print(f"   UI Port: {user_session.blender_ui_port}")
        
        agent = BlenderChatAgent(
            api_key=api_key,
            mcp_host=mcp_host,
            mcp_port=9876  # Internal port
        )
        
        # Initialize MCP connection using await (we're in an async function)
        num_tools = await agent.initialize_mcp()
        
        # Test actual Blender connection by calling a simple tool
        try:
            test_result = await agent.call_mcp_tool("get_scene_info", {})
            
            # Check both the success flag and result content for errors
            result_str = str(test_result.get("result", "")).lower()
            
            # The MCP server returns "Unknown tool" when Blender isn't connected
            # or returns error messages containing connection failures
            if (not test_result.get("success", False) or 
                "unknown tool" in result_str or
                "connection refused" in result_str or 
                "could not connect" in result_str or
                "error executing" in result_str or
                "failed to connect" in result_str):
                await agent.cleanup()
                agent = None
                return ConnectionStatus(
                    connected=False,
                    error="Blender MCP addon is not running. Please enable the addon in Blender."
                )
            
            # Connection successful - clear the scene for a fresh start
            try:
                clear_result = await agent.call_mcp_tool("execute_blender_code", {
                    "code": """import bpy
# Clear all mesh objects from the scene
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        bpy.data.objects.remove(obj, do_unlink=True)
# Clear unused mesh data
for mesh in bpy.data.meshes:
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
print('Scene cleared - ready for new objects')"""
                })
                print(f"✅ Scene cleared on connection for user {user_id}")
            except Exception as clear_error:
                # Don't fail connection if scene clearing fails
                print(f"⚠️ Warning: Could not clear scene on connect: {clear_error}")
            
            return ConnectionStatus(
                connected=True,
                num_tools=num_tools
            )
        except Exception as test_error:
            # Test call failed, cleanup and return error
            await agent.cleanup()
            agent = None
            return ConnectionStatus(
                connected=False,
                error=f"Blender MCP addon is not running. Please enable the addon in Blender. ({str(test_error)})"
            )
    
    except Exception as e:
        if agent:
            await agent.cleanup()
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
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent not connected"
        )
    
    return {"history": agent.conversation_history}


@app.post("/refine-prompt", response_model=RefinePromptResponse)
async def refine_prompt(request: RefinePromptRequest):
    """Refine a user prompt into a comprehensive 3D modeling description (DEPRECATED - use /refine-prompt/start for long tasks)"""
    global refinement_agent
    
    # Handle "as-is" detail level - skip refinement
    if request.detail_level == "as-is":
        print(f"📝 Using prompt as-is (no refinement): {request.prompt[:100]}...")
        return RefinePromptResponse(
            refined_prompt=request.prompt,
            reasoning_steps=["Used prompt as-is without refinement"],
            is_detailed=True,
            original_prompt=request.prompt
        )
    
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


@app.post("/refine-prompt/start", response_model=RefinePromptJobResponse)
async def start_refinement_job(request: RefinePromptJobRequest):
    """Start a background refinement job for long-running tasks"""
    global refinement_agent, refinement_jobs
    
    # Handle "as-is" detail level - skip refinement
    if request.detail_level == "as-is":
        job_id = f"asis_{int(time.time())}"
        refinement_jobs[job_id] = {
            "status": "completed",
            "result": {
                "refined_prompt": request.prompt,
                "reasoning_steps": ["Used prompt as-is without refinement"],
                "is_detailed": True,
                "original_prompt": request.prompt
            }
        }
        return RefinePromptJobResponse(
            job_id=job_id,
            status="completed",
            message="Prompt used as-is"
        )
    
    if not refinement_agent:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Prompt refinement agent not available"
        )
    
    # Generate job ID
    import uuid
    job_id = str(uuid.uuid4())[:12]
    
    # Initialize job tracking
    refinement_jobs[job_id] = {
        "status": "pending",
        "prompt": request.prompt,
        "detail_level": request.detail_level,
        "started_at": time.time(),
        "progress": "Initializing refinement..."
    }
    
    # Start background task
    async def run_refinement():
        try:
            refinement_jobs[job_id]["status"] = "processing"
            refinement_jobs[job_id]["progress"] = "Analyzing prompt..."
            
            print(f"\n🧠 [Job {job_id}] Starting refinement: {request.prompt[:100]}...")
            
            result = refinement_agent.refine_prompt(
                user_prompt=request.prompt,
                thread_id=job_id,
                detail_level=request.detail_level
            )
            
            refinement_jobs[job_id]["status"] = "completed"
            refinement_jobs[job_id]["result"] = result
            refinement_jobs[job_id]["completed_at"] = time.time()
            
            elapsed = time.time() - refinement_jobs[job_id]["started_at"]
            print(f"✅ [Job {job_id}] Refinement complete in {elapsed:.1f}s: {len(result['refined_prompt'])} characters")
            
        except Exception as e:
            import traceback
            error_msg = f"Error during refinement: {str(e)}"
            print(f"❌ [Job {job_id}] {error_msg}\n{traceback.format_exc()}")
            
            refinement_jobs[job_id]["status"] = "failed"
            refinement_jobs[job_id]["error"] = error_msg
            refinement_jobs[job_id]["completed_at"] = time.time()
    
    # Run in background
    asyncio.create_task(run_refinement())
    
    return RefinePromptJobResponse(
        job_id=job_id,
        status="pending",
        message=f"Refinement job {job_id} started. Poll /refine-prompt/status/{job_id} for updates."
    )


@app.get("/refine-prompt/status/{job_id}", response_model=RefinePromptJobStatus)
async def get_refinement_status(job_id: str):
    """Check the status of a refinement job"""
    global refinement_jobs
    
    if job_id not in refinement_jobs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job {job_id} not found"
        )
    
    job = refinement_jobs[job_id]
    
    response = RefinePromptJobStatus(
        job_id=job_id,
        status=job["status"],
        progress=job.get("progress")
    )
    
    if job["status"] == "completed":
        result = job["result"]
        response.refined_prompt = result["refined_prompt"]
        response.reasoning_steps = result["reasoning_steps"]
        response.is_detailed = result["is_detailed"]
        response.original_prompt = result["original_prompt"]
    elif job["status"] == "failed":
        response.error = job.get("error")
    
    return response


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
        
        # Create cancellation check function
        def is_cancelled():
            return artisan_tasks.get(task_id, {}).get("cancelled", False)
        
        # Create new artisan agent instance for this task with cancellation support
        task_agent = ArtisanAgent(cancellation_check=is_cancelled)
        
        # Store task info
        artisan_tasks[task_id] = {
            "status": "initializing",
            "agent": task_agent,
            "requirement_file": request.requirement_file,
            "use_resume": request.use_resume,
            "result": None,
            "error": None,
            "messages": [],  # Add message log
            "progress": 0,  # Add progress tracking
            "cancelled": False  # Add cancellation flag
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
    
    def log_message(msg: str):
        """Helper to log messages"""
        print(f"[Task {task_id}] {msg}")
        task_info["messages"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    try:
        # Check if cancelled before starting
        if task_info.get("cancelled", False):
            task_info["status"] = "cancelled"
            task_info["progress"] = 0
            log_message("Task cancelled before initialization")
            return
        
        # Update status
        task_info["status"] = "running"
        task_info["progress"] = 10
        
        # Initialize agent
        log_message("Initializing Artisan Agent...")
        await agent.initialize()
        
        # Check cancellation after initialization
        if task_info.get("cancelled", False):
            task_info["status"] = "cancelled"
            task_info["progress"] = 0
            log_message("Task cancelled after initialization")
            return
        
        task_info["progress"] = 20
        log_message("Agent initialized successfully")
        
        # Run modeling task
        log_message(f"Running modeling task: {task_info['requirement_file']}")
        task_info["progress"] = 30
        
        result = await agent.run(
            task_info["requirement_file"],
            use_deterministic_session=task_info["use_resume"]
        )
        
        # Check if cancelled after completion (task may have been cancelled mid-execution)
        if task_info.get("cancelled", False):
            task_info["status"] = "cancelled"
            task_info["progress"] = 0
            log_message("Task was cancelled during execution")
            return
        
        # Store result
        task_info["result"] = result
        task_info["session_id"] = result.get("session_id")
        task_info["steps_executed"] = result.get("steps_executed", 0)
        
        # Check if recursion limit was reached
        if result.get("recursion_limit_reached", False) or result.get("partial_completion", False):
            task_info["status"] = "partial_completion"
            steps_done = result.get("steps_executed", 0)
            total_steps = result.get("total_steps", 0)
            
            if total_steps > 0:
                # Calculate progress percentage
                task_info["progress"] = int((steps_done / total_steps) * 100)
            else:
                task_info["progress"] = 50  # Unknown progress
            
            resume_msg = (
                f"Recursion limit reached. Completed {steps_done}/{total_steps} steps. "
                f"Use 'Enable Resume Mode' and run again to continue from step {steps_done + 1}."
            )
            log_message(resume_msg)
            task_info["resume_info"] = resume_msg
        elif result.get("success", False):
            task_info["status"] = "completed"
            task_info["progress"] = 100
            log_message("Completed successfully")
        else:
            # Incomplete but not due to recursion limit
            task_info["status"] = "completed"
            task_info["progress"] = 90
            log_message("Workflow finished (may be incomplete)")
        
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        task_info["error"] = str(e)
        task_info["status"] = "failed"
        task_info["progress"] = 0
        log_message(f"Failed: {str(e)}")
        print(f"[Task {task_id}] Full error:\n{error_msg}")
        
    finally:
        # Cleanup agent
        try:
            await agent.cleanup()
            log_message("Agent cleaned up")
        except Exception as e:
            log_message(f"Error during cleanup: {e}")


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
        error=task_info.get("error"),
        messages=task_info.get("messages", []),
        progress=task_info.get("progress", 0)
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


@app.post("/artisan/cancel/{task_id}")
async def cancel_artisan_task(task_id: str):
    """Cancel a running artisan modeling task"""
    global artisan_tasks
    
    if task_id not in artisan_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_info = artisan_tasks[task_id]
    
    # Only cancel if task is running or initializing
    if task_info["status"] in ["initializing", "running"]:
        task_info["cancelled"] = True
        task_info["status"] = "cancelled"
        task_info["progress"] = 0
        task_info["messages"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Task cancelled by user")
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancellation requested"
        }
    else:
        return {
            "task_id": task_id,
            "status": task_info["status"],
            "message": f"Task cannot be cancelled (current status: {task_info['status']})"
        }


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/signup", response_model=SignupResponse)
async def signup(request: SignupRequest):
    """Create a new user account"""
    global auth_service
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        # Validate input
        if len(request.username) < 3:
            return SignupResponse(
                success=False,
                message="Username must be at least 3 characters long"
            )
        
        if len(request.password) < 6:
            return SignupResponse(
                success=False,
                message="Password must be at least 6 characters long"
            )
        
        # Create user
        new_user = auth_service.create_user(request.username, request.password)
        
        if new_user:
            return SignupResponse(
                success=True,
                user_id=new_user["id"],
                username=new_user["username"],
                message="User created successfully"
            )
        else:
            return SignupResponse(
                success=False,
                message="Username already exists"
            )
    
    except Exception as e:
        import traceback
        error_detail = f"Error during signup: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user and return JWT token"""
    global auth_service, session_manager
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        result = auth_service.authenticate_user(request.username, request.password)
        
        if result:
            # Create or get user's Blender session (async, non-blocking)
            user_session = None
            if session_manager:
                try:
                    # Try to get existing session first (fast)
                    existing_session = session_manager.get_user_session(result["user_id"])
                    if existing_session:
                        user_session = existing_session
                        print(f"✅ Retrieved existing Blender session for {result['username']}")
                    else:
                        # Create new session (may take 10-15 seconds)
                        print(f"🚀 Creating Blender container for {result['username']}...")
                        user_session = session_manager.create_user_session(
                            user_id=result["user_id"],
                            username=result["username"]
                        )
                        print(f"✅ Created Blender session for {result['username']}")
                    
                    print(f"   MCP Port: {user_session.mcp_port}")
                    print(f"   Blender UI Port: {user_session.blender_ui_port}")
                except Exception as e:
                    print(f"⚠️ Failed to create user session: {e}")
                    import traceback
                    traceback.print_exc()
            
            return LoginResponse(
                success=True,
                token=result["token"],
                user_id=result["user_id"],
                username=result["username"],
                expires_at=result["expires_at"],
                message="Login successful",
                mcp_port=user_session.mcp_port if user_session else None,
                blender_ui_port=user_session.blender_ui_port if user_session else None,
                blender_ui_url=user_session.blender_ui_url if user_session and hasattr(user_session, 'blender_ui_url') else None
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
    global auth_service, session_manager
    
    if not auth_service:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not available"
        )
    
    try:
        # Get user info from token before invalidating
        payload = auth_service.verify_token(request.token)
        
        # Invalidate token
        auth_service.logout(request.token)
        
        # Remove user's Blender session (stop and delete container)
        if session_manager and payload:
            user_id = payload.get("user_id")
            if user_id:
                try:
                    session_manager.remove_user_session(user_id)
                    print(f"🗑️ Removed Blender container for user {payload.get('username')} (ID: {user_id})")
                except Exception as e:
                    print(f"⚠️ Error stopping user session: {e}")
        
        return {"success": True, "message": "Logged out successfully"}
    
    except Exception as e:
        import traceback
        error_detail = f"Error during logout: {str(e)}\n{traceback.format_exc()}"
        print(error_detail)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/user/session")
async def get_user_session_info(user_id: int):
    """Get user's Blender session information"""
    global session_manager
    
    if not session_manager:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session manager not available"
        )
    
    session = session_manager.get_user_session(user_id)
    
    if not session:
        return {
            "active": False,
            "message": "No active session"
        }
    
    # Kubernetes mode
    if hasattr(session, 'service_name'):
        return {
            "active": True,
            "user_id": session.user_id,
            "username": session.username,
            "pod_name": session.pod_name,
            "service_name": session.service_name,
            "mcp_port": session.mcp_port,
            "blender_ui_port": session.blender_ui_port,
            "blender_ui_url": session.blender_ui_url or f"http://{session.service_name}.{session.namespace}.svc.cluster.local:3000",
            "external_ip": session.external_ip,
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }
    # Docker mode
    else:
        return {
            "active": True,
            "user_id": session.user_id,
            "username": session.username,
            "container_name": session.container_name,
            "mcp_port": session.mcp_port,
            "blender_ui_port": session.blender_ui_port,
            "blender_ui_url": f"http://localhost:{session.blender_ui_port}",
            "created_at": session.created_at.isoformat(),
            "last_activity": session.last_activity.isoformat()
        }


if __name__ == "__main__":
    import uvicorn
    
    # Run the server with increased timeouts for rate-limited API calls
    uvicorn.run(
        "backend_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        timeout_keep_alive=300,  # 5 minutes
        timeout_graceful_shutdown=30
    )
