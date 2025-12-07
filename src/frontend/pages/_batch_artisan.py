"""Batch Artisan Agent Page
Loads refined prompts from JSON files and runs the Artisan agent
"""
import streamlit as st
import sys
from pathlib import Path
import json
import time
from datetime import datetime

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Try multiple import paths
try:
    from config import get_backend_url
    from backend.api_client import BlenderChatAPIClient
except ImportError:
    try:
        from src.config import get_backend_url
        from src.backend.api_client import BlenderChatAPIClient
    except ImportError:
        def get_backend_url():
            return "http://backend:8000"
        # Fallback import
        sys.path.insert(0, str(src_path / "src" / "backend"))
        from api_client import BlenderChatAPIClient

import requests

# Get backend URL
BACKEND_URL = get_backend_url()


def verify_authentication():
    """Check if user is authenticated, redirect to login if not"""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("⚠️ Please login first")
        time.sleep(1)
        st.switch_page("pages/_auth.py")
        return False
    
    if "token" not in st.session_state or not st.session_state.token:
        st.error("⚠️ Session expired. Please login again.")
        time.sleep(1)
        st.switch_page("pages/_auth.py")
        return False
    
    # Verify token is still valid
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/verify",
            json={"token": st.session_state.token},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if not data.get("valid", False):
                st.session_state.authenticated = False
                st.session_state.token = None
                st.error("⚠️ Session expired. Please login again.")
                time.sleep(1)
                st.switch_page("pages/_auth.py")
                return False
        else:
            st.session_state.authenticated = False
            st.session_state.token = None
            st.switch_page("pages/_auth.py")
            return False
    
    except Exception:
        st.error("⚠️ Unable to verify session. Please login again.")
        time.sleep(1)
        st.switch_page("pages/_auth.py")
        return False
    
    return True


def logout_user():
    """Logout user and clean up session"""
    try:
        if st.session_state.get("token"):
            response = requests.post(
                f"{BACKEND_URL}/auth/logout",
                json={"token": st.session_state.token},
                timeout=10  # Increased timeout for container cleanup
            )
            if response.status_code == 200:
                st.success("🗑️ Logged out and container removed")
    except Exception as e:
        st.warning(f"Logout warning: {e}")
    
    # Clear all session state
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None
    st.session_state.user_id = None
    st.session_state.blender_ui_url = None
    st.session_state.mcp_port = None
    st.session_state.blender_ui_port = None
    st.session_state.connected = False


def load_json_files():
    """Load available JSON requirement files"""
    json_dir = Path("data/prompts/json")
    if not json_dir.exists():
        json_dir.mkdir(parents=True, exist_ok=True)
        return []
    
    json_files = list(json_dir.glob("*.json"))
    return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)


def display_json_preview(json_path: Path):
    """Display preview of JSON requirement"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Original:** {data.get('original_prompt', 'N/A')}")
            st.markdown(f"**Timestamp:** {data.get('timestamp', 'N/A')}")
        with col2:
            st.markdown(f"**Detailed:** {'✅' if data.get('is_detailed', False) else '❌'}")
            refined_length = len(data.get('refined_prompt', ''))
            st.markdown(f"**Length:** {refined_length:,} characters")
        
        refined = data.get('refined_prompt', '')
        if refined:
            preview_length = min(500, len(refined))
            st.text_area(
                "Refined Prompt Preview",
                refined[:preview_length] + ("..." if len(refined) > preview_length else ""),
                height=150,
                disabled=True,
                key=f"preview_{json_path.name}"
            )
    except Exception as e:
        st.error(f"Error loading preview: {e}")


def start_modeling_task(requirement_file: str, use_resume: bool, enable_refinement: bool, token: str):
    """Start a modeling task via backend API"""
    try:
        # Load the JSON file to modify it with enable_refinement setting
        with open(requirement_file, 'r', encoding='utf-8') as f:
            requirement_data = json.load(f)
        
        # Update the enable_refinement_steps field
        requirement_data['enable_refinement_steps'] = enable_refinement
        
        # Save the modified data back to the file
        with open(requirement_file, 'w', encoding='utf-8') as f:
            json.dump(requirement_data, f, indent=2, ensure_ascii=False)
        
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/artisan/model",
            json={
                "requirement_file": str(requirement_file),
                "use_resume": use_resume
            },
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to start modeling task: {str(e)}")


def get_task_status(task_id: str, token: str):
    """Get status of a modeling task"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BACKEND_URL}/artisan/status/{task_id}",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
        # Task not found (404) or other HTTP errors
        if e.response.status_code == 404:
            return {
                "status": "not_found",
                "message": f"Task {task_id} not found (backend may have restarted)"
            }
        return {"status": "http_error", "message": str(e)}
    except requests.exceptions.Timeout:
        return {"status": "timeout", "message": "Request timed out"}
    except requests.exceptions.ConnectionError:
        return {"status": "connection_error", "message": "Cannot connect to backend"}
    except Exception as e:
        return {"status": "unknown_error", "message": str(e)}


def stop_modeling_task(task_id: str, token: str):
    """Stop/cancel a running modeling task"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/artisan/cancel/{task_id}",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to stop task: {str(e)}")


def main():
    """Main page function"""
    st.set_page_config(
        page_title="Batch Artisan Agent",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Check authentication first
    if not verify_authentication():
        return
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("📦 Batch Artisan Agent")
    
    with col2:
        st.info(f"👤 {st.session_state.get('username', 'User')}")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.switch_page("pages/_auth.py")
    
    st.markdown("*Load refined prompts from JSON and run autonomous 3D modeling*")
    
    # Info banner
    st.info("💡 This page runs the Artisan agent using pre-refined prompts saved as JSON files in `data/prompts/json/`")
    
    # Initialize API client in session state
    if 'blender_client' not in st.session_state:
        st.session_state.blender_client = BlenderChatAPIClient()
    
    if 'blender_connected' not in st.session_state:
        st.session_state.blender_connected = False
    
    # Sidebar
    with st.sidebar:
        # Page Navigation at the top
        st.subheader("📄 Navigate")
        col_nav1, col_nav2 = st.columns(2)
        with col_nav1:
            if st.button("🏠 Home", use_container_width=True, key="nav_home"):
                st.switch_page("pages/artisan_app.py")
        with col_nav2:
            if st.button("🎨 Artisan", use_container_width=True, key="nav_artisan"):
                st.switch_page("pages/_artisan_agent.py")
        st.markdown("---")
        
        st.header("⚙️ Configuration")
        
        # Blender connection status
        st.subheader("🔌 Blender Connection")
        backend_status = st.session_state.blender_client.health_check()
        
        if backend_status:
            st.success("✅ Backend Connected")
            
            if not st.session_state.blender_connected:
                if st.button("🔌 Connect to Blender", use_container_width=True):
                    with st.spinner("Connecting to Blender..."):
                        result = st.session_state.blender_client.connect()
                        if result.get("connected"):
                            st.session_state.blender_connected = True
                            st.success(f"Connected! {result.get('num_tools', 0)} tools available")
                            st.rerun()
                        else:
                            st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
            else:
                st.success("✅ Blender Connected")
                if st.button("🔌 Disconnect", use_container_width=True):
                    st.session_state.blender_client.disconnect()
                    st.session_state.blender_connected = False
                    st.rerun()
        else:
            st.error("❌ Backend Offline")
            st.info("Make sure the backend container is running")
        
        st.divider()
        
        # Load available JSON files
        json_files = load_json_files()
        
        st.subheader("📄 Select Requirement File")
        
        # Show current recursion limit from environment
        import os
        recursion_limit = os.getenv("LANGGRAPH_RECURSION_LIMIT", "100")
        st.info(f"🔄 LangGraph Recursion Limit: **{recursion_limit}**")
        
        if not json_files:
            st.warning("No JSON files found in data/prompts/json/")
            st.info("💡 Create requirements using the **Prompt Refinement** page first!")
            selected_file = None
        else:
            # File selector
            file_options = {f.name: f for f in json_files}
            selected_name = st.selectbox(
                "Available Requirements",
                options=list(file_options.keys()),
                help="Select a JSON requirement file to process"
            )
            
            selected_file = file_options[selected_name]
            
            # Preview
            with st.expander("📋 Preview Requirement", expanded=False):
                display_json_preview(selected_file)
        
        st.divider()
        
        # Options
        st.subheader("⚙️ Options")
        use_resume = st.checkbox(
            "Enable Resume Mode",
            value=True,
            help="If enabled, the agent will continue from previous work on the same file"
        )
        
        enable_refinement_steps = st.checkbox(
            "Enable Refinement Steps",
            value=False,
            help="When enabled, the agent will refine steps that don't meet quality thresholds. When disabled, it will proceed to the next step regardless of quality."
        )
        
        if enable_refinement_steps:
            st.info("✅ Agent will refine low-quality steps automatically")
        else:
            st.warning("⚠️ Agent will skip refinement and proceed with all steps")
        
        st.divider()
        
        # Execution controls
        st.subheader("🚀 Execution")
        
        if 'batch_running' not in st.session_state:
            st.session_state.batch_running = False
        
        # Disable start button if: no file selected, already running, or not connected to Blender
        start_disabled = selected_file is None or st.session_state.batch_running or not st.session_state.blender_connected
        
        if not st.session_state.blender_connected:
            st.warning("⚠️ Connect to Blender first")
        
        if st.button("🎬 Start Modeling", disabled=start_disabled, use_container_width=True):
            st.session_state.batch_running = True
            st.session_state.batch_task_id = None
            st.rerun()
        
        if st.session_state.batch_running:
            if st.button("🛑 Stop", use_container_width=True, type="primary"):
                # Cancel the backend task
                if st.session_state.get("batch_task_id"):
                    try:
                        result = stop_modeling_task(
                            st.session_state.batch_task_id,
                            st.session_state.token
                        )
                        st.success(f"✅ {result.get('message', 'Task stopped')}")
                    except Exception as e:
                        st.warning(f"⚠️ {str(e)}")
                
                st.session_state.batch_running = False
                st.rerun()
    
    # Main content area
    if selected_file is None:
        st.info("👈 Select a requirement file from the sidebar to get started")
        
        # Show instructions
        with st.expander("📖 How to Use", expanded=True):
            st.markdown("""
            ### Workflow
            
            1. **Create a refined prompt:**
               - Go to the **Prompt Refinement** page
               - Enter your 3D modeling idea
               - Let the AI refine it with detailed specifications
               - The refined prompt is saved as JSON in `data/prompts/json/`
            
            2. **Load and execute:**
               - Come to this page
               - Select your saved JSON file from the sidebar
               - Click **Start Modeling**
               - Watch the agent work in real-time
            
            3. **View results:**
               - Open Blender Web UI at http://localhost:3000
               - See your 3D model being created live
            
            ### Features
            
            - ✅ **Resume Mode**: Continue from where the agent left off
            - ✅ **Real-time Status**: Monitor agent progress
            - ✅ **Tool Execution**: See each Blender command executed
            """)
    
    elif st.session_state.batch_running:
        # Show execution status
        status_container = st.container()
        progress_container = st.container()
        log_container = st.container()
        
        # Start task if not already started
        if 'batch_task_id' not in st.session_state or st.session_state.batch_task_id is None:
            with status_container:
                with st.spinner("Starting modeling task..."):
                    try:
                        result = start_modeling_task(str(selected_file), use_resume, enable_refinement_steps, st.session_state.token)
                        st.session_state.batch_task_id = result.get('task_id')
                        st.success(f"✅ Task started: {st.session_state.batch_task_id}")
                    except Exception as e:
                        st.error(f"❌ Failed to start task: {e}")
                        st.session_state.batch_running = False
                        st.stop()
        
        # Poll for status
        task_id = st.session_state.batch_task_id
        
        with status_container:
            status_placeholder = st.empty()
        
        with progress_container:
            progress_bar = st.progress(0)
            progress_text = st.empty()
        
        with log_container:
            st.subheader("📋 Execution Log")
            log_placeholder = st.empty()
        
        # Polling loop
        max_iterations = 300  # 5 minutes max
        iteration = 0
        
        while st.session_state.batch_running and iteration < max_iterations:
            try:
                status_data = get_task_status(task_id, st.session_state.token)
                
                task_status = status_data.get('status', 'unknown')
                
                # Handle special error cases
                if task_status == 'not_found':
                    status_placeholder.error("**Status:** Task not found")
                    st.error(f"⚠️ {status_data.get('message', 'Task not found')}. The backend may have restarted. Please start a new task.")
                    st.session_state.batch_running = False
                    break
                elif task_status in ['connection_error', 'timeout', 'http_error', 'unknown_error']:
                    status_placeholder.warning(f"**Status:** {task_status}")
                    error_msg = status_data.get('message', 'Communication error')
                    st.warning(f"⚠️ {error_msg}. Retrying...")
                    time.sleep(5)  # Wait longer before retry
                    iteration += 1
                    continue
                
                # Update status for normal cases
                if task_status == 'failed':
                    status_placeholder.error(f"**Status:** {task_status}")
                elif task_status in ['initializing', 'running']:
                    status_placeholder.info(f"**Status:** {task_status}")
                elif task_status == 'partial_completion':
                    status_placeholder.warning(f"**Status:** Recursion limit reached (partial completion)")
                elif task_status == 'completed':
                    status_placeholder.success(f"**Status:** {task_status}")
                elif task_status == 'cancelled':
                    status_placeholder.warning(f"**Status:** {task_status}")
                else:
                    status_placeholder.info(f"**Status:** {task_status}")
                
                # Update progress (use actual progress from backend)
                progress = status_data.get('progress', 0)
                progress_bar.progress(min(progress / 100, 1.0))
                progress_text.text(f"Progress: {progress}%")
                
                # Show error if present
                error_msg = status_data.get('error')
                if error_msg:
                    st.error(f"**Error Details:** {error_msg}")
                
                # Show resume info if present (for partial completion)
                resume_info = status_data.get('resume_info')
                if resume_info:
                    st.info(f"ℹ️ **Resume Information:** {resume_info}")
                
                # Update log with messages from backend
                messages = status_data.get('messages', [])
                if messages:
                    log_text = "\n".join(messages[-30:])  # Last 30 messages
                    log_placeholder.code(log_text, language="text")
                else:
                    # Fallback log if no messages yet
                    log_messages = []
                    log_messages.append(f"Task ID: {task_id}")
                    log_messages.append(f"Status: {task_status}")
                    
                    if status_data.get('session_id'):
                        log_messages.append(f"Session ID: {status_data['session_id']}")
                    
                    if status_data.get('steps_executed', 0) > 0:
                        log_messages.append(f"Steps executed: {status_data['steps_executed']}")
                    
                    log_text = "\n".join(log_messages)
                    log_placeholder.code(log_text, language="text")
                
                # Check if done
                if task_status in ['completed', 'failed', 'cancelled', 'partial_completion']:
                    st.session_state.batch_running = False
                    if task_status == 'completed':
                        st.success("✅ Modeling task completed!")
                        st.balloons()
                    elif task_status == 'partial_completion':
                        st.warning("⚠️ Task paused - Recursion limit reached")
                        st.info("💡 **How to continue:** Enable 'Resume Mode' in the sidebar and click 'Start Modeling' again to continue from where it left off.")
                        # Show detailed progress
                        steps_done = status_data.get('steps_executed', 0)
                        if steps_done > 0:
                            st.info(f"📊 Progress: {steps_done} steps completed")
                    elif task_status == 'cancelled':
                        st.warning("⚠️ Task was cancelled")
                    else:
                        st.error(f"❌ Task {task_status}")
                    
                    # Wait a moment for user to see the completion message
                    # time.sleep(2)
                    # st.rerun()  # Refresh UI to update button states
                    break
                
                time.sleep(2)
                iteration += 1
                
            except Exception as e:
                st.error(f"Error polling status: {e}")
                break
        
        if iteration >= max_iterations:
            st.warning("⏱️ Status polling timed out. Task may still be running.")
    
    else:
        # Idle state - show file info
        st.subheader("📄 Selected File")
        st.code(str(selected_file), language="text")
        
        st.info("👈 Click **Start Modeling** in the sidebar to begin")
        
        # Show full JSON preview
        with st.expander("📋 Full JSON Content", expanded=False):
            try:
                with open(selected_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                st.json(data)
            except Exception as e:
                st.error(f"Error loading JSON: {e}")


if __name__ == "__main__":
    main()
