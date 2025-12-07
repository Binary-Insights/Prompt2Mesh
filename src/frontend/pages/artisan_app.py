"""
Artisan App - Main workspace for authenticated users
Multi-page app with Artisan Agent and Batch Artisan
"""
import streamlit as st
import requests
import time
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from config import get_backend_url
except ImportError:
    from src.config import get_backend_url

# Backend API configuration
BACKEND_URL = get_backend_url()


def verify_authentication():
    """Check if user is authenticated"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.error("⚠️ Please login first to access this page")
        time.sleep(1)
        st.switch_page("pages/_auth.py")
        st.stop()
    
    if "token" not in st.session_state or not st.session_state.token:
        st.error("⚠️ Session expired. Please login again.")
        time.sleep(1)
        st.switch_page("pages/_auth.py")
        st.stop()
    
    return True


# Verify authentication before anything else
verify_authentication()

# Page config
st.set_page_config(
    page_title="Prompt2Mesh - Artisan Workspace",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded"
)


def logout_user(token: str):
    """Logout user and clean up container"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json={"token": token},
            timeout=10
        )
        return response.status_code == 200
    except Exception:
        return False


def show_header():
    """Show common header with user info and logout"""
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.title("🎨 Prompt2Mesh - Artisan Workspace")
    
    with col2:
        st.info(f"👤 {st.session_state.get('username', 'User')}")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            token = st.session_state.get("token")
            logout_user(token)
            
            # Clear all session state
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.username = None
            if 'user_id' in st.session_state:
                del st.session_state.user_id
            if 'blender_ui_url' in st.session_state:
                del st.session_state.blender_ui_url
            if 'mcp_port' in st.session_state:
                del st.session_state.mcp_port
            if 'blender_ui_port' in st.session_state:
                del st.session_state.blender_ui_port
            if 'connected' in st.session_state:
                del st.session_state.connected
            
            st.success("🗑️ Logged out and container removed")
            time.sleep(1)
            st.switch_page("pages/_auth.py")
    
    st.markdown("---")
    
    # Session info
    if st.session_state.get("blender_ui_url"):
        col_a, col_b = st.columns([2, 1])
        with col_a:
            st.markdown(f"**🎨 Blender UI:** [{st.session_state.blender_ui_url}]({st.session_state.blender_ui_url})")
        with col_b:
            if st.button("🔄 Refresh Connection", use_container_width=True):
                st.rerun()


# Show common header
show_header()

# Sidebar info
with st.sidebar:
    st.title("📍 Artisan Workspace")
    st.markdown("---")
    
    # Page Navigation
    st.subheader("📄 Pages")
    
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🏠 Home", use_container_width=True, key="nav_home"):
            st.switch_page("pages/artisan_app.py")
    with col_b:
        if st.button("🎨 Artisan", use_container_width=True, key="nav_artisan"):
            st.switch_page("pages/_artisan_agent.py")
    
    if st.button("📦 Batch Artisan", use_container_width=True, key="nav_batch"):
        st.switch_page("pages/_batch_artisan.py")
    
    st.markdown("---")
    
    # Connection details
    with st.expander("🔌 Connection Details", expanded=False):
        st.write(f"**User ID:** {st.session_state.get('user_id', 'N/A')}")
        st.write(f"**MCP Port:** {st.session_state.get('mcp_port', 'N/A')}")
        st.write(f"**UI Port:** {st.session_state.get('blender_ui_port', 'N/A')}")

# Main content
st.info("👈 Use the sidebar to navigate between Artisan Agent and Batch Artisan pages")

# Navigation state
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Page selection in sidebar
with st.sidebar:
    st.markdown("---")
    st.subheader("📄 Pages")
    
    if st.button("🏠 Home", use_container_width=True, 
                type="primary" if st.session_state.current_page == "home" else "secondary"):
        st.session_state.current_page = "home"
        st.rerun()
    
    if st.button("🎨 Artisan Agent", use_container_width=True, 
                type="primary" if st.session_state.current_page == "artisan" else "secondary"):
        st.session_state.current_page = "artisan"
        st.rerun()
    
    if st.button("📦 Batch Artisan", use_container_width=True,
                type="primary" if st.session_state.current_page == "batch" else "secondary"):
        st.session_state.current_page = "batch"
        st.rerun()

# Display selected page content
if st.session_state.current_page == "home":
    st.markdown("""
    ### Welcome to your Artisan Workspace!

    **Available Tools:**
    - **🎨 Artisan Agent**: Interactive chat interface for 3D modeling
    - **📦 Batch Artisan**: Process multiple prompts from JSON files

    Navigate using the sidebar to get started.
    """)
elif st.session_state.current_page == "artisan":
    # Import and execute artisan agent page
    st.switch_page("pages/_artisan_agent.py")
elif st.session_state.current_page == "batch":
    # Import and execute batch artisan page
    st.switch_page("pages/_batch_artisan.py")
