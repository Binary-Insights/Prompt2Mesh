"""
Streamlit Interface for Artisan Agent
Provides web UI for running 3D modeling tasks via Backend API
"""
import streamlit as st
import requests
import time
import sys
from pathlib import Path
from datetime import datetime
import json

# Backend API configuration
BACKEND_URL = "http://localhost:8000"


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


class StreamlitDisplay:
    """Display adapter for Streamlit"""
    
    def __init__(self):
        self.messages = []
    
    def __call__(self, message: str, type: str = "info"):
        """Display message in Streamlit"""
        icons = {
            "info": "ℹ️",
            "success": "✅",
            "error": "❌",
            "tool": "🔧",
            "plan": "📋",
            "screenshot": "📸",
            "thinking": "🤔"
        }
        
        icon = icons.get(type, "•")
        self.messages.append(f"{icon} {message}")
        
        # Display based on type
        if type == "error":
            st.error(f"{icon} {message}")
        elif type == "success":
            st.success(f"{icon} {message}")
        elif type == "info":
            st.info(f"{icon} {message}")
        else:
            st.write(f"{icon} {message}")


def load_json_files():
    """Load available JSON requirement files"""
    json_dir = Path("data/prompts/json")
    if not json_dir.exists():
        return []
    
    json_files = list(json_dir.glob("*.json"))
    return sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)


def display_json_preview(json_path: Path):
    """Display preview of JSON requirement"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        st.markdown("**Preview:**")
        st.markdown(f"- **Original:** {data.get('original_prompt', 'N/A')}")
        st.markdown(f"- **Timestamp:** {data.get('timestamp', 'N/A')}")
        st.markdown(f"- **Detailed:** {data.get('is_detailed', False)}")
        
        refined = data.get('refined_prompt', '')
        if refined:
            preview_length = min(500, len(refined))
            st.text_area(
                "Refined Prompt Preview",
                refined[:preview_length] + ("..." if len(refined) > preview_length else ""),
                height=150,
                disabled=True
            )
    except Exception as e:
        st.error(f"Error loading preview: {e}")


def main():
    st.set_page_config(
        page_title="Artisan Agent - 3D Modeling",
        page_icon="🎨",
        layout="wide"
    )
    
    st.title("🎨 Artisan Agent - Autonomous 3D Modeling")
    st.markdown("*AI-powered agent that builds 3D models in Blender from requirements*")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Session ID
        if 'session_id' not in st.session_state:
            st.session_state.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        session_id = st.text_input(
            "Session ID",
            value=st.session_state.session_id,
            help="Unique identifier for this modeling session"
        )
        
        st.divider()
        
        # Load available JSON files
        json_files = load_json_files()
        
        st.subheader("📄 Select Requirement File")
        
        if not json_files:
            st.warning("No JSON files found in data/prompts/json/")
            st.info("Create requirements using the Prompt Refinement agent first")
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
            with st.expander("📋 Preview Requirement"):
                display_json_preview(selected_file)
        
        st.divider()
        
        # Resume mode
        st.subheader("⚙️ Options")
        use_resume = st.checkbox(
            "Enable Resume Mode",
            value=True,
            help="If enabled, the agent will continue from previous work on the same file"
        )
        
        st.divider()
        
        # Execution controls
        st.subheader("🚀 Execution")
        
        if 'running' not in st.session_state:
            st.session_state.running = False
        
        start_disabled = selected_file is None or st.session_state.running
        
        if st.button("🎬 Start Modeling", disabled=start_disabled, use_container_width=True):
            st.session_state.running = True
            st.rerun()
        
        if st.session_state.running:
            if st.button("🛑 Stop", use_container_width=True):
                st.session_state.running = False
                st.rerun()
    
    # Main area
    if st.session_state.running and selected_file:
        st.header("🔄 Modeling in Progress")
        
        # Check backend status
        if not check_backend_status():
            st.error("❌ Backend server is not running!")
            st.info("Start the backend server with: `python src/backend/backend_server.py`")
            st.session_state.running = False
            st.stop()
        
        # Progress container
        progress_container = st.container()
        
        with progress_container:
            st.info(f"Processing: {selected_file.name}")
            
            try:
                # Start modeling task
                with st.spinner("Starting modeling task..."):
                    task_response = start_modeling_task(
                        requirement_file=str(selected_file.absolute()),
                        use_resume=use_resume
                    )
                    task_id = task_response["task_id"]
                    st.success(f"✅ Task started with ID: {task_id}")
                
                # Poll for status
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                poll_count = 0
                max_polls = 600  # 10 minutes max (600 * 1 second)
                
                while poll_count < max_polls:
                    # Get task status
                    status_response = get_task_status(task_id)
                    task_status = status_response["status"]
                    
                    # Update progress
                    steps_executed = status_response.get("steps_executed", 0)
                    status_text.text(f"Status: {task_status} | Steps: {steps_executed}")
                    
                    if task_status == "completed":
                        progress_bar.progress(100)
                        st.success("✅ Modeling Complete!")
                        
                        # Display results
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Steps Executed", status_response['steps_executed'])
                        with col2:
                            st.metric("Screenshots", status_response['screenshots_captured'])
                        with col3:
                            st.metric("Success", "✅" if status_response['success'] else "❌")
                        
                        # Screenshot directory
                        st.info(f"📁 Screenshots saved in: `{status_response['screenshot_directory']}`")
                        
                        # Tool results
                        if status_response.get('tool_results'):
                            with st.expander("🔧 Tool Execution Details"):
                                for i, tool_result in enumerate(status_response['tool_results'], 1):
                                    status_icon = "✅" if tool_result.get('success', False) else "❌"
                                    st.markdown(f"**{i}. {status_icon} {tool_result['tool_name']}**")
                                    st.code(json.dumps(tool_result.get('arguments', {}), indent=2))
                                    if not tool_result.get('success', False):
                                        st.error(f"Error: {tool_result.get('result', '')}")
                                    st.divider()
                        
                        # Display screenshots
                        screenshot_dir = Path(status_response.get('screenshot_directory', ''))
                        if screenshot_dir.exists():
                            screenshots = sorted(screenshot_dir.glob("*.png"))
                            if screenshots:
                                st.subheader("📸 Viewport Screenshots")
                                
                                cols = st.columns(3)
                                for idx, screenshot in enumerate(screenshots):
                                    with cols[idx % 3]:
                                        st.image(str(screenshot), caption=screenshot.name, use_container_width=True)
                        
                        break
                    
                    elif task_status == "failed":
                        progress_bar.progress(0)
                        st.error(f"❌ Task Failed: {status_response.get('error', 'Unknown error')}")
                        break
                    
                    elif task_status in ["running", "initializing"]:
                        # Update progress based on steps
                        progress_value = min(95, int((steps_executed / 10) * 100))  # Cap at 95%
                        progress_bar.progress(progress_value)
                        time.sleep(1)  # Poll every second
                    
                    poll_count += 1
                
                if poll_count >= max_polls:
                    st.warning("⚠️ Task is taking longer than expected. Check backend logs for status.")
                
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                import traceback
                with st.expander("🔍 Error Details"):
                    st.code(traceback.format_exc())
            
            finally:
                st.session_state.running = False
                if st.button("🔄 Run Another Task", use_container_width=True):
                    st.rerun()
    
    else:
        # Welcome screen
        st.header("👋 Welcome to Artisan Agent")
        
        # Check backend status
        backend_online = check_backend_status()
        if backend_online:
            st.success("✅ Backend server is running")
        else:
            st.error("❌ Backend server is not running")
            st.warning("Please start the backend server:")
            st.code("python src/backend/backend_server.py", language="bash")
        
        st.markdown("""
        ### What is Artisan Agent?
        
        Artisan Agent is an autonomous AI agent that creates 3D models in Blender by:
        
        1. 📖 **Reading** detailed modeling requirements from JSON files
        2. 🧠 **Planning** sequential steps to complete the task
        3. 🔧 **Executing** Blender MCP tools to build the model
        4. 📸 **Capturing** viewport screenshots for visual feedback
        5. 🔄 **Iterating** until the model is complete
        
        ### How to Use
        
        1. Select a requirement JSON file from the sidebar
        2. Review the requirement preview
        3. Click "Start Modeling" to begin
        4. Watch the agent work in real-time
        5. Review results and screenshots when complete
        
        ### Requirements Format
        
        The agent reads JSON files from `data/prompts/json/` with this structure:
        ```json
        {
          "refined_prompt": "Detailed 3D modeling description...",
          "original_prompt": "Simple user request",
          "timestamp": "2025-11-27 13:55:57"
        }
        ```
        
        Use the **Prompt Refinement Agent** to generate these requirement files.
        """)
        
        # Example command
        st.divider()
        st.subheader("🖥️ Command Line Usage")
        st.code("""
# Run as standalone script
python src/artisan_agent/run_artisan.py --input-file data/prompts/json/your_file.json

# With custom session ID
python src/artisan_agent/run_artisan.py -i path/to/file.json -s my-session-123

# Verbose mode
python src/artisan_agent/run_artisan.py -i path/to/file.json -v
        """, language="bash")


if __name__ == "__main__":
    main()
