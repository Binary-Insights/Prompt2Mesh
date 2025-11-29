"""
Batch Artisan Agent Page
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
except ImportError:
    try:
        from src.config import get_backend_url
    except ImportError:
        def get_backend_url():
            return "http://backend:8000"

import requests

# Get backend URL
BACKEND_URL = get_backend_url()


def check_auth():
    """Check if user is authenticated"""
    if 'token' not in st.session_state:
        st.warning("⚠️ Please login first")
        st.stop()
    return st.session_state.token


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


def start_modeling_task(requirement_file: str, use_resume: bool, token: str):
    """Start a modeling task via backend API"""
    try:
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
    except Exception as e:
        return {"status": "error", "message": str(e)}


def main():
    """Main page function"""
    st.set_page_config(
        page_title="Batch Artisan Agent",
        page_icon="📦",
        layout="wide"
    )
    
    # Check authentication
    token = check_auth()
    
    st.title("📦 Batch Artisan Agent")
    st.markdown("*Load refined prompts from JSON and run autonomous 3D modeling*")
    
    # Info banner
    st.info("💡 This page runs the Artisan agent using pre-refined prompts saved as JSON files in `data/prompts/json/`")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Load available JSON files
        json_files = load_json_files()
        
        st.subheader("📄 Select Requirement File")
        
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
        
        st.divider()
        
        # Execution controls
        st.subheader("🚀 Execution")
        
        if 'batch_running' not in st.session_state:
            st.session_state.batch_running = False
        
        start_disabled = selected_file is None or st.session_state.batch_running
        
        if st.button("🎬 Start Modeling", disabled=start_disabled, use_container_width=True):
            st.session_state.batch_running = True
            st.session_state.batch_task_id = None
            st.rerun()
        
        if st.session_state.batch_running:
            if st.button("🛑 Stop", use_container_width=True):
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
            - ✅ **Screenshots**: Visual feedback from Blender
            """)
    
    elif st.session_state.batch_running:
        # Run the modeling task
        st.subheader("🎬 Modeling in Progress")
        
        status_container = st.container()
        progress_container = st.container()
        log_container = st.container()
        
        # Start task if not already started
        if 'batch_task_id' not in st.session_state or st.session_state.batch_task_id is None:
            with status_container:
                with st.spinner("Starting modeling task..."):
                    try:
                        result = start_modeling_task(selected_file, use_resume, token)
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
                status_data = get_task_status(task_id, token)
                
                task_status = status_data.get('status', 'unknown')
                
                # Update status
                if task_status == 'failed' or task_status == 'error':
                    status_placeholder.error(f"**Status:** {task_status}")
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
                if task_status in ['completed', 'failed', 'error']:
                    st.session_state.batch_running = False
                    if task_status == 'completed':
                        st.success("✅ Modeling task completed!")
                        st.balloons()
                    else:
                        st.error(f"❌ Task {task_status}")
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
