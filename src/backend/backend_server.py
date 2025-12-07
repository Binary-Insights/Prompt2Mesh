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
from src.sculptor_agent import SculptorAgent
from src.login import AuthService, init_db

# Load environment variables
load_dotenv()

# Global agent instances
agent: BlenderChatAgent = None
refinement_agent: PromptRefinementAgent = None
artisan_agent: ArtisanAgent = None
artisan_tasks: Dict[str, Dict[str, Any]] = {}  # Track running tasks
sculptor_agent: SculptorAgent = None
sculptor_tasks: Dict[str, Dict[str, Any]] = {}  # Track sculptor tasks
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
    messages: List[str] = []  # Add messages list
    progress: int = 0  # Add progress percentage


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


class SculptorModelingRequest(BaseModel):
    """Request model for sculptor modeling endpoint"""
    image_path: str  # Path to input 2D image
    use_resume: bool = True


class SculptorModelingResponse(BaseModel):
    """Response model for sculptor modeling endpoint"""
    task_id: str
    status: str  # "started", "running", "completed", "failed"
    message: str


class SculptorTaskStatus(BaseModel):
    """Response model for sculptor task status"""
    task_id: str
    status: str
    session_id: Optional[str] = None
    steps_executed: int = 0
    screenshots_captured: int = 0
    screenshot_directory: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    tool_results: List[Dict[str, Any]] = []
    messages: List[str] = []
    progress: int = 0
    vision_analysis: Optional[str] = None
    quality_scores: List[Dict[str, Any]] = []


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
                "tasks": "/artisan/tasks",
                "cancel": "/artisan/cancel/{task_id}"
            },
            "sculptor": {
                "model": "/sculptor/model",
                "status": "/sculptor/status/{task_id}",
                "tasks": "/sculptor/tasks",
                "cancel": "/sculptor/cancel/{task_id}"
            }
        },
        "auth_available": auth_service is not None,
        "refinement_agent_available": refinement_agent is not None,
        "artisan_agent_available": artisan_agent is not None,
        "sculptor_agent_available": sculptor_agent is not None
    }


@app.post("/connect", response_model=ConnectionStatus)
async def connect():
    """Connect to Blender MCP server"""
    global agent, agent_loop
    
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
        
        # Create new agent
        agent = BlenderChatAgent(api_key=api_key)
        
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
# Sculptor Agent Endpoints
# ============================================================================

@app.post("/sculptor/model", response_model=SculptorModelingResponse)
async def start_sculptor_modeling(request: SculptorModelingRequest):
    """Start a Sculptor Agent modeling task from 2D image"""
    global sculptor_agent, sculptor_tasks
    
    # Validate image file exists
    image_file = Path(request.image_path)
    if not image_file.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Image file not found: {request.image_path}"
        )
    
    try:
        # Generate task ID
        from uuid import uuid4
        task_id = str(uuid4())
        
        # Create sculptor agent for this task
        agent = SculptorAgent(
            session_id=task_id,
            display_callback=None,
            cancellation_check=lambda: sculptor_tasks.get(task_id, {}).get("cancelled", False)
        )
        
        # Store task info
        sculptor_tasks[task_id] = {
            "task_id": task_id,
            "agent": agent,
            "image_path": request.image_path,
            "use_resume": request.use_resume,
            "status": "initializing",
            "result": None,
            "error": None,
            "messages": [],
            "progress": 0,
            "cancelled": False
        }
        
        # Start background task
        asyncio.create_task(_run_sculptor_task(task_id))
        
        return SculptorModelingResponse(
            task_id=task_id,
            status="initializing",
            message="Sculptor task started"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start sculptor task: {str(e)}"
        )


async def _run_sculptor_task(task_id: str):
    """Background task runner for sculptor modeling"""
    global sculptor_tasks
    
    task_info = sculptor_tasks[task_id]
    agent = task_info["agent"]
    
    def log_message(msg: str):
        """Helper to log messages"""
        print(f"[Sculptor {task_id}] {msg}")
        task_info["messages"].append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
    
    try:
        # Check if cancelled before starting
        if task_info.get("cancelled", False):
            log_message("Task cancelled before execution")
            task_info["status"] = "cancelled"
            return
        
        # Update status
        task_info["status"] = "running"
        task_info["progress"] = 10
        
        # Initialize agent
        log_message("Initializing Sculptor Agent...")
        await agent.initialize()
        
        # Check cancellation after initialization
        if task_info.get("cancelled", False):
            log_message("Task cancelled after initialization")
            task_info["status"] = "cancelled"
            return
        
        task_info["progress"] = 20
        log_message("Agent initialized successfully")
        
        # Run modeling task
        log_message(f"Analyzing image: {task_info['image_path']}")
        task_info["progress"] = 30
        
        result = await agent.run(
            task_info["image_path"],
            use_deterministic_session=task_info["use_resume"]
        )
        
        # Check if cancelled after completion
        if task_info.get("cancelled", False):
            log_message("Task cancelled after execution")
            task_info["status"] = "cancelled"
            return
        
        # Store result
        task_info["result"] = result
        task_info["session_id"] = result.get("session_id")
        task_info["steps_executed"] = result.get("steps_executed", 0)
        task_info["screenshots_captured"] = result.get("screenshots_captured", 0)
        task_info["screenshot_directory"] = result.get("screenshot_directory")
        task_info["vision_analysis"] = result.get("vision_analysis")
        task_info["quality_scores"] = result.get("quality_scores", [])
        
        # Check if recursion limit was reached
        if result.get("recursion_limit_reached", False):
            task_info["status"] = "completed"
            task_info["progress"] = 100
            log_message(f"Completed with recursion limit (steps: {task_info['steps_executed']})")
        elif result.get("success", False):
            task_info["status"] = "completed"
            task_info["progress"] = 100
            log_message("Modeling completed successfully")
        else:
            task_info["status"] = "failed"
            task_info["error"] = result.get("error", "Unknown error")
            task_info["progress"] = 0
            log_message(f"Failed: {task_info['error']}")
            
    except Exception as e:
        import traceback
        error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
        task_info["error"] = str(e)
        task_info["status"] = "failed"
        task_info["progress"] = 0
        log_message(f"Failed: {str(e)}")
        print(f"[Sculptor {task_id}] Full error:\n{error_msg}")
        
    finally:
        # Cleanup agent
        try:
            await agent.cleanup()
        except Exception as e:
            log_message(f"Cleanup error: {str(e)}")


@app.get("/sculptor/status/{task_id}", response_model=SculptorTaskStatus)
async def get_sculptor_task_status(task_id: str):
    """Get the status of a sculptor modeling task"""
    global sculptor_tasks
    
    if task_id not in sculptor_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_info = sculptor_tasks[task_id]
    result = task_info.get("result")
    
    # Build response
    response = SculptorTaskStatus(
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
        response.vision_analysis = result.get("vision_analysis")
        response.quality_scores = result.get("quality_scores", [])
    
    return response


@app.get("/sculptor/tasks")
async def list_sculptor_tasks():
    """List all sculptor modeling tasks"""
    global sculptor_tasks
    
    tasks_summary = []
    for task_id, info in sculptor_tasks.items():
        tasks_summary.append({
            "task_id": task_id,
            "status": info["status"],
            "image_path": info["image_path"],
            "use_resume": info["use_resume"],
            "progress": info.get("progress", 0)
        })
    
    return {
        "tasks": tasks_summary,
        "total": len(tasks_summary)
    }


@app.post("/sculptor/cancel/{task_id}")
async def cancel_sculptor_task(task_id: str):
    """Cancel a running sculptor modeling task"""
    global sculptor_tasks
    
    if task_id not in sculptor_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found"
        )
    
    task_info = sculptor_tasks[task_id]
    
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
