"""
Sculptor Agent Page
Upload 2D images and convert them to 3D models using AI vision
"""
import streamlit as st
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import base64

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
        sys.path.insert(0, str(src_path / "src" / "backend"))
        from api_client import BlenderChatAPIClient

# Get backend URL
BACKEND_URL = get_backend_url()


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
                st.error("⚠️ Session expired. Please login again.")
                st.session_state.authenticated = False
                st.session_state.token = None
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


def save_uploaded_image(uploaded_file) -> str:
    """Save uploaded image to data directory and return path"""
    # Create directory for sculptor images
    image_dir = Path("data/sculptor_images")
    image_dir.mkdir(parents=True, exist_ok=True)
    
    # Create filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{timestamp}_{uploaded_file.name}"
    filepath = image_dir / filename
    
    # Save file
    with open(filepath, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return str(filepath)


def start_sculptor_task(image_path: str, use_resume: bool, token: str):
    """Start a sculptor modeling task via backend API"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/sculptor/model",
            json={
                "image_path": image_path,
                "use_resume": use_resume
            },
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise Exception(f"Failed to start sculptor task: {str(e)}")


def get_sculptor_status(task_id: str, token: str):
    """Get status of a sculptor modeling task"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(
            f"{BACKEND_URL}/sculptor/status/{task_id}",
            headers=headers,
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as e:
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


def stop_sculptor_task(task_id: str, token: str):
    """Stop/cancel a running sculptor task"""
    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            f"{BACKEND_URL}/sculptor/cancel/{task_id}",
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
        page_title="Sculptor Agent",
        page_icon="🗿",
        layout="wide"
    )
    
    # Check authentication first
    if not verify_authentication():
        return
    
    # Header with user info and logout
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("🗿 Sculptor Agent")
    
    with col2:
        st.info(f"👤 {st.session_state.get('username', 'User')}")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.switch_page("login_page.py")
    
    st.markdown("*Transform 2D images into 3D models using AI vision*")
    
    # Info banner
    st.info("💡 Upload a 2D image and the Sculptor agent will analyze it and autonomously create a 3D model in Blender")
    
    # Initialize API client in session state
    if 'blender_client' not in st.session_state:
        st.session_state.blender_client = BlenderChatAPIClient()
    
    if 'blender_connected' not in st.session_state:
        st.session_state.blender_connected = False
    
    if 'sculptor_running' not in st.session_state:
        st.session_state.sculptor_running = False
    
    if 'uploaded_image_path' not in st.session_state:
        st.session_state.uploaded_image_path = None
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Blender connection status
        st.subheader("🔌 Blender Connection")
        backend_status = st.session_state.blender_client.health_check()
        
        if backend_status:
            st.success("✅ Backend Connected")
            
            if not st.session_state.blender_connected:
                if st.button("🔗 Connect to Blender", use_container_width=True):
                    with st.spinner("Connecting to Blender..."):
                        result = st.session_state.blender_client.connect()
                        if result.get("connected"):
                            st.session_state.blender_connected = True
                            st.success(f"✅ Connected! ({result.get('num_tools', 0)} tools)")
                            st.rerun()
                        else:
                            st.error(f"❌ Connection failed: {result.get('error', 'Unknown error')}")
            else:
                st.success(f"✅ Blender Connected")
                if st.button("🔌 Disconnect", use_container_width=True):
                    st.session_state.blender_client.disconnect()
                    st.session_state.blender_connected = False
                    st.rerun()
        else:
            st.error("❌ Backend Offline")
            st.info("Make sure the backend container is running")
        
        st.divider()
        
        # Image upload
        st.subheader("📸 Input Image")
        
        uploaded_file = st.file_uploader(
            "Upload 2D Image",
            type=["png", "jpg", "jpeg", "bmp"],
            help="Upload an image to convert to 3D"
        )
        
        if uploaded_file is not None:
            # Display preview
            image = Image.open(uploaded_file)
            st.image(image, caption="Input Image", use_container_width=True)
            
            # Save to disk when first uploaded
            if st.session_state.uploaded_image_path is None or not Path(st.session_state.uploaded_image_path).exists():
                with st.spinner("Saving image..."):
                    image_path = save_uploaded_image(uploaded_file)
                    st.session_state.uploaded_image_path = image_path
                    st.success(f"✅ Saved: {Path(image_path).name}")
        
        st.divider()
        
        # Options
        st.subheader("⚙️ Options")
        use_resume = st.checkbox(
            "Enable Resume Mode",
            value=True,
            help="If enabled, the agent will continue from previous work on the same image"
        )
        
        st.divider()
        
        # Execution controls
        st.subheader("🚀 Execution")
        
        # Disable start button if: no image uploaded, already running, or not connected to Blender
        start_disabled = (
            st.session_state.uploaded_image_path is None or 
            st.session_state.sculptor_running or 
            not st.session_state.blender_connected
        )
        
        if not st.session_state.blender_connected:
            st.warning("⚠️ Connect to Blender first")
        elif st.session_state.uploaded_image_path is None:
            st.warning("⚠️ Upload an image first")
        
        if st.button("🎨 Start Sculpting", disabled=start_disabled, use_container_width=True):
            st.session_state.sculptor_running = True
            st.session_state.sculptor_task_id = None
            st.rerun()
        
        if st.session_state.sculptor_running:
            if st.button("🛑 Stop", use_container_width=True, type="primary"):
                if st.session_state.get("sculptor_task_id"):
                    try:
                        stop_sculptor_task(st.session_state.sculptor_task_id, st.session_state.token)
                        st.success("Task stopped")
                    except Exception as e:
                        st.error(f"Error stopping task: {e}")
                st.session_state.sculptor_running = False
                st.rerun()
    
    # Main content area
    if st.session_state.uploaded_image_path is None:
        st.info("👈 Upload a 2D image from the sidebar to get started")
        
        # Show instructions
        with st.expander("📖 How to Use", expanded=True):
            st.markdown("""
            ### Workflow
            
            1. **Upload an image:**
               - Click "Upload 2D Image" in the sidebar
               - Choose a PNG, JPG, or other image file
               - The image can be a photo, drawing, or sketch
            
            2. **Start sculpting:**
               - Click **Start Sculpting**
               - The AI will analyze your image
               - It will plan modeling steps automatically
               - Watch the 3D model being created live
            
            3. **View results:**
               - Open Blender Web UI at http://localhost:3000
               - See your 3D model being created in real-time
               - The agent will iteratively refine the model
            
            ### Features
            
            - ✅ **Vision-Based Planning**: AI analyzes your image and creates a custom plan
            - ✅ **Dynamic Steps**: Steps are generated based on image complexity
            - ✅ **Iterative Refinement**: Agent compares screenshots with input and improves
            - ✅ **Resume Mode**: Continue from where the agent left off
            - ✅ **Real-time Feedback**: Monitor progress with visual comparisons
            
            ### Tips
            
            - 📌 Use clear, well-lit images for best results
            - 📌 Simple objects work better than complex scenes
            - 📌 Front-facing views are easier to model
            - 📌 Images with clear shapes and forms work best
            """)
    
    elif st.session_state.sculptor_running:
        # Show execution status
        status_container = st.container()
        progress_container = st.container()
        log_container = st.container()
        
        # Start task if not already started
        if 'sculptor_task_id' not in st.session_state or st.session_state.sculptor_task_id is None:
            with status_container:
                with st.spinner("Starting sculptor task..."):
                    try:
                        result = start_sculptor_task(
                            st.session_state.uploaded_image_path,
                            use_resume,
                            st.session_state.token
                        )
                        st.session_state.sculptor_task_id = result["task_id"]
                        st.success(f"✅ Task started: {result['task_id'][:8]}...")
                    except Exception as e:
                        st.error(f"❌ Failed to start task: {e}")
                        st.session_state.sculptor_running = False
                        st.stop()
        
        # Poll for status
        task_id = st.session_state.sculptor_task_id
        
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
        
        while st.session_state.sculptor_running and iteration < max_iterations:
            try:
                status_data = get_sculptor_status(task_id, st.session_state.token)
                
                # Handle error states
                if status_data.get("status") in ["not_found", "http_error", "timeout", "connection_error", "unknown_error"]:
                    with status_placeholder:
                        st.error(f"❌ Error: {status_data.get('message', 'Unknown error')}")
                    st.session_state.sculptor_running = False
                    break
                
                current_status = status_data.get("status", "unknown")
                
                # Update status display
                with status_placeholder:
                    if current_status == "initializing":
                        st.info("🔄 Initializing sculptor agent...")
                    elif current_status == "running":
                        st.info("🎨 Sculpting in progress...")
                    elif current_status == "completed":
                        if status_data.get("success", False):
                            st.success("✅ Sculpting completed successfully!")
                        else:
                            st.warning("⚠️ Sculpting completed with issues")
                        st.session_state.sculptor_running = False
                    elif current_status == "failed":
                        st.error(f"❌ Sculpting failed: {status_data.get('error', 'Unknown error')}")
                        st.session_state.sculptor_running = False
                    elif current_status == "cancelled":
                        st.warning("⚠️ Task was cancelled")
                        st.session_state.sculptor_running = False
                
                # Update progress bar
                progress = status_data.get("progress", 0)
                progress_bar.progress(progress / 100.0)
                
                steps_done = status_data.get("steps_executed", 0)
                screenshots = status_data.get("screenshots_captured", 0)
                progress_text.markdown(f"**Progress:** {progress}% | Steps: {steps_done} | Screenshots: {screenshots}")
                
                # Update logs
                messages = status_data.get("messages", [])
                if messages:
                    log_text = "\n".join(messages[-20:])  # Show last 20 messages
                    log_placeholder.code(log_text, language="text")
                
                # If completed or failed, show final results
                if current_status in ["completed", "failed", "cancelled"]:
                    st.divider()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📊 Statistics")
                        st.metric("Steps Executed", steps_done)
                        st.metric("Screenshots", screenshots)
                        st.metric("Success", "✅" if status_data.get("success") else "❌")
                    
                    with col2:
                        st.subheader("📁 Output")
                        if status_data.get("screenshot_directory"):
                            st.code(status_data["screenshot_directory"], language="text")
                        
                        if status_data.get("vision_analysis"):
                            with st.expander("👁️ Vision Analysis"):
                                st.markdown(status_data["vision_analysis"][:500] + "...")
                    
                    # Quality scores
                    if status_data.get("quality_scores"):
                        st.subheader("📈 Quality Progression")
                        scores = status_data["quality_scores"]
                        
                        import pandas as pd
                        df = pd.DataFrame([
                            {"Step": s["step"], "Quality": s["score"]}
                            for s in scores
                        ])
                        st.line_chart(df.set_index("Step"))
                    
                    break
                
                # Wait before next poll
                time.sleep(2)
                iteration += 1
                
            except Exception as e:
                st.error(f"❌ Error polling status: {e}")
                st.session_state.sculptor_running = False
                break
        
        if iteration >= max_iterations:
            st.warning("⏱️ Status polling timed out. Task may still be running.")
    
    else:
        # Idle state - show image info
        st.subheader("📸 Selected Image")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            if st.session_state.uploaded_image_path:
                try:
                    image = Image.open(st.session_state.uploaded_image_path)
                    st.image(image, caption="Input Image", use_container_width=True)
                except Exception as e:
                    st.error(f"Error loading image: {e}")
        
        with col2:
            st.code(str(st.session_state.uploaded_image_path), language="text")
            
            if st.session_state.uploaded_image_path:
                path_obj = Path(st.session_state.uploaded_image_path)
                st.markdown(f"**Filename:** {path_obj.name}")
                st.markdown(f"**Size:** {path_obj.stat().st_size / 1024:.1f} KB")
                
                try:
                    image = Image.open(st.session_state.uploaded_image_path)
                    st.markdown(f"**Dimensions:** {image.width} x {image.height}")
                    st.markdown(f"**Format:** {image.format}")
                except:
                    pass
        
        st.info("👈 Click **Start Sculpting** in the sidebar to begin")


if __name__ == "__main__":
    main()
