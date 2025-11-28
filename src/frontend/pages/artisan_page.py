"""
Artisan Agent page - Protected by authentication
"""
import streamlit as st
import requests
import time
from pathlib import Path
from datetime import datetime
import json

# Backend API configuration
BACKEND_URL = "http://localhost:8000"


def verify_authentication():
    """Check if user is authenticated, redirect to login if not"""
    if "authenticated" not in st.session_state or not st.session_state.authenticated:
        st.error("⚠️ Please login first")
        time.sleep(1)
        st.switch_page("login_page.py")
        return False
    
    if "token" not in st.session_state or not st.session_state.token:
        st.error("⚠️ Session expired. Please login again.")
        time.sleep(1)
        st.switch_page("login_page.py")
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
                st.switch_page("login_page.py")
                return False
        else:
            st.session_state.authenticated = False
            st.session_state.token = None
            st.switch_page("login_page.py")
            return False
    
    except Exception:
        st.error("⚠️ Unable to verify session. Please login again.")
        time.sleep(1)
        st.switch_page("login_page.py")
        return False
    
    return True


def logout_user():
    """Logout user"""
    try:
        if st.session_state.get("token"):
            requests.post(
                f"{BACKEND_URL}/auth/logout",
                json={"token": st.session_state.token},
                timeout=5
            )
    except Exception:
        pass
    
    st.session_state.authenticated = False
    st.session_state.token = None
    st.session_state.username = None


def check_backend_status():
    """Check if backend server is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=2)
        return response.status_code == 200
    except:
        return False


def start_modeling_task(requirement_file: str, use_resume: bool = True) -> dict:
    """Start a modeling task via API"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/artisan/model",
            json={
                "requirement_file": requirement_file,
                "use_resume": use_resume
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to start modeling task: {str(e)}")


def get_task_status(task_id: str) -> dict:
    """Get status of a modeling task"""
    try:
        response = requests.get(
            f"{BACKEND_URL}/artisan/status/{task_id}",
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to get task status: {str(e)}")


def main():
    """Main Artisan Agent interface"""
    st.set_page_config(
        page_title="Artisan Agent - Prompt2Mesh",
        page_icon="🎨",
        layout="wide"
    )
    
    # Check authentication first
    if not verify_authentication():
        return
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("🎨 Artisan Agent - Autonomous 3D Modeling")
    
    with col2:
        st.info(f"👤 {st.session_state.get('username', 'User')}")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.switch_page("login_page.py")
    
    st.markdown("---")
    
    # Check backend status
    backend_online = check_backend_status()
    
    if not backend_online:
        st.error("❌ Backend server is offline")
        st.code("python src/backend/backend_server.py", language="bash")
        return
    
    st.success("✅ Backend server is online")
    
    # Main interface
    st.header("📋 Modeling Task Configuration")
    
    # File selection
    project_root = Path(__file__).parent.parent.parent
    requirements_dir = project_root / "requirements"
    
    # Get list of requirement files
    requirement_files = []
    if requirements_dir.exists():
        requirement_files = sorted([f.name for f in requirements_dir.glob("*.json")])
    
    if not requirement_files:
        st.warning("⚠️ No requirement files found in 'requirements/' directory")
        st.info("Create a JSON requirement file to get started")
        return
    
    # File selector
    selected_file = st.selectbox(
        "Select Requirement File",
        options=requirement_files,
        help="Choose a JSON file containing modeling requirements"
    )
    
    # Session resume option
    use_resume = st.checkbox(
        "Enable Session Resume",
        value=True,
        help="Continue from previous session if available"
    )
    
    # Display file preview
    if selected_file:
        file_path = requirements_dir / selected_file
        
        with st.expander("📄 View Requirements", expanded=False):
            try:
                with open(file_path, 'r') as f:
                    requirements_data = json.load(f)
                st.json(requirements_data)
            except Exception as e:
                st.error(f"Error reading file: {str(e)}")
    
    st.markdown("---")
    
    # Start modeling button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("🚀 Start Modeling Task", use_container_width=True, type="primary"):
            if not selected_file:
                st.error("Please select a requirement file")
                return
            
            # Start task
            file_path = str(requirements_dir / selected_file)
            
            with st.spinner("🎬 Starting modeling task..."):
                try:
                    result = start_modeling_task(file_path, use_resume)
                    task_id = result.get("task_id")
                    
                    if task_id:
                        st.success(f"✅ Task started! ID: {task_id}")
                        
                        # Store task ID in session state
                        st.session_state.current_task_id = task_id
                        st.session_state.task_running = True
                        
                        st.rerun()
                    else:
                        st.error("Failed to start task")
                
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    st.markdown("---")
    
    # Task monitoring section
    if st.session_state.get("task_running") and st.session_state.get("current_task_id"):
        st.header("📊 Task Progress")
        
        task_id = st.session_state.current_task_id
        
        # Create placeholders for dynamic updates
        status_placeholder = st.empty()
        progress_placeholder = st.empty()
        details_placeholder = st.empty()
        
        # Poll for status updates
        max_iterations = 600  # 10 minutes max (600 seconds / 1 second interval)
        iteration = 0
        
        while iteration < max_iterations:
            try:
                status_data = get_task_status(task_id)
                
                task_status = status_data.get("status", "unknown")
                steps_executed = status_data.get("steps_executed", 0)
                screenshots_captured = status_data.get("screenshots_captured", 0)
                
                # Update status
                status_placeholder.info(f"**Status:** {task_status.upper()}")
                
                # Update progress bar (estimate total steps as 15)
                estimated_total = 15
                progress_value = min(steps_executed / estimated_total, 1.0)
                progress_placeholder.progress(
                    progress_value,
                    text=f"Progress: {steps_executed} steps executed"
                )
                
                # Display details
                with details_placeholder.container():
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Steps Executed", steps_executed)
                    
                    with col2:
                        st.metric("Screenshots Captured", screenshots_captured)
                
                # Check if task is complete
                if task_status == "completed":
                    st.success("✅ Task completed successfully!")
                    
                    # Display results
                    st.subheader("📸 Results")
                    
                    screenshot_dir = status_data.get("screenshot_directory")
                    if screenshot_dir:
                        st.info(f"Screenshots saved to: {screenshot_dir}")
                    
                    # Display session info
                    session_id = status_data.get("session_id")
                    if session_id:
                        st.info(f"Session ID: {session_id}")
                    
                    # Clear running state
                    st.session_state.task_running = False
                    
                    # Show restart button
                    if st.button("🔄 Start New Task"):
                        st.session_state.current_task_id = None
                        st.rerun()
                    
                    break
                
                elif task_status == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    st.error(f"❌ Task failed: {error_msg}")
                    
                    st.session_state.task_running = False
                    
                    if st.button("🔄 Start New Task"):
                        st.session_state.current_task_id = None
                        st.rerun()
                    
                    break
                
                # Wait before next poll
                time.sleep(1)
                iteration += 1
            
            except Exception as e:
                st.error(f"Error getting task status: {str(e)}")
                break
        
        if iteration >= max_iterations:
            st.warning("⏱️ Monitoring timeout reached")
            st.session_state.task_running = False


if __name__ == "__main__":
    main()
