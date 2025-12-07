"""
Authentication App - Login and Signup
Standalone app for user authentication
"""
import streamlit as st
import requests
import time
from pathlib import Path
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from config import get_backend_url

# Backend API configuration
BACKEND_URL = get_backend_url()

# Page config
st.set_page_config(
    page_title="Prompt2Mesh - Authentication",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)


def check_backend_status() -> bool:
    """Check if backend server is online"""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def login_user(username: str, password: str):
    """Authenticate user with backend"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data
        return None
    except Exception as e:
        st.error(f"Login error: {e}")
        return None


def signup_user(username: str, password: str):
    """Create new user account"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/signup",
            json={"username": username, "password": password},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("success", False)
        return False
    except Exception as e:
        st.error(f"Signup error: {e}")
        return False


def login_page():
    """Login page UI"""
    st.title("🔐 Prompt2Mesh Login")
    st.markdown("---")
    
    # Check backend status
    backend_online = check_backend_status()
    
    if backend_online:
        st.success("✅ Backend server is online")
    else:
        st.error("❌ Backend server is offline. Please start the backend server first.")
        st.code("docker-compose up -d", language="bash")
        return
    
    # Login form
    st.subheader("Sign In")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        submit_button = st.form_submit_button("🔑 Login", use_container_width=True)
        
        if submit_button:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                with st.spinner("🔐 Authenticating and setting up your Blender instance..."):
                    result = login_user(username, password)
                    
                    if result:
                        # Store authentication info in session state
                        st.session_state.authenticated = True
                        st.session_state.token = result["token"]
                        st.session_state.username = result["username"]
                        st.session_state.user_id = result.get("user_id")
                        st.session_state.blender_ui_url = result.get("blender_ui_url")
                        st.session_state.mcp_port = result.get("mcp_port")
                        st.session_state.blender_ui_port = result.get("blender_ui_port")
                        
                        st.success(f"✅ Welcome, {result['username']}!")
                        
                        # Show Blender UI info if available
                        if result.get("blender_ui_url"):
                            st.info(f"🎨 Your Blender instance: {result['blender_ui_url']}")
                            st.markdown(f"**[🚀 Open Blender UI]({result['blender_ui_url']})**", unsafe_allow_html=True)
                            st.caption("Click the link above to open your Blender interface in a new tab")
                        
                        time.sleep(1)
                        st.info("🎨 Redirecting to Artisan workspace...")
                        time.sleep(1)
                        
                        # Redirect to artisan app
                        st.switch_page("pages/artisan_app.py")
                    else:
                        st.error("❌ Invalid username or password")
    
    st.markdown("---")
    st.info("""
    **Default Credentials:**
    - Username: `root`
    - Password: `root`
    """)


def signup_page():
    """Signup page UI"""
    st.title("📝 Create New Account")
    st.markdown("---")
    
    # Check backend status
    backend_online = check_backend_status()
    
    if backend_online:
        st.success("✅ Backend server is online")
    else:
        st.error("❌ Backend server is offline. Please start the backend server first.")
        return
    
    # Signup form
    st.subheader("Sign Up")
    
    with st.form("signup_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        password_confirm = st.text_input("Confirm Password", type="password", placeholder="Re-enter your password")
        
        submit_button = st.form_submit_button("📝 Create Account", use_container_width=True)
        
        if submit_button:
            if not username or not password or not password_confirm:
                st.error("Please fill in all fields")
            elif password != password_confirm:
                st.error("❌ Passwords do not match")
            elif len(password) < 4:
                st.error("❌ Password must be at least 4 characters long")
            else:
                with st.spinner("Creating your account..."):
                    success = signup_user(username, password)
                    
                    if success:
                        st.success("✅ Account created successfully!")
                        time.sleep(1)
                        st.info("Redirecting to login page...")
                        time.sleep(1)
                        st.session_state.page = "login"
                        st.rerun()
                    else:
                        st.error("❌ Username already exists or signup failed")
    
    st.markdown("---")
    st.caption("Already have an account? Use the navigation above.")


def main():
    """Main authentication app with page navigation"""
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "page" not in st.session_state:
        st.session_state.page = "login"
    
    # Check if already authenticated
    if st.session_state.authenticated:
        st.switch_page("pages/artisan_app.py")
        return
    
    # Navigation tabs
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Sign Up"])
    
    with tab1:
        login_page()
    
    with tab2:
        signup_page()


if __name__ == "__main__":
    main()
