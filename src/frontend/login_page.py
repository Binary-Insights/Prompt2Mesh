"""
Login page for Prompt2Mesh application
"""
import streamlit as st
import requests
import time
from typing import Optional

# Backend API configuration
BACKEND_URL = "http://localhost:8000"


def check_backend_status() -> bool:
    """Check if backend server is online"""
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


def login_user(username: str, password: str) -> Optional[dict]:
    """
    Authenticate user with backend
    
    Returns:
        Dict with token and user info if successful, None otherwise
    """
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                return data
        
        return None
    
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return None


def verify_token(token: str) -> bool:
    """Verify if token is still valid"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/verify",
            json={"token": token},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("valid", False)
        
        return False
    
    except Exception:
        return False


def logout_user(token: str) -> bool:
    """Logout user by invalidating token"""
    try:
        response = requests.post(
            f"{BACKEND_URL}/auth/logout",
            json={"token": token},
            timeout=5
        )
        
        return response.status_code == 200
    
    except Exception:
        return False


def main():
    """Main login page"""
    st.set_page_config(
        page_title="Prompt2Mesh - Login",
        page_icon="🔐",
        layout="centered"
    )
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "token" not in st.session_state:
        st.session_state.token = None
    if "username" not in st.session_state:
        st.session_state.username = None
    
    # Check if already authenticated
    if st.session_state.authenticated and st.session_state.token:
        # Verify token is still valid
        if verify_token(st.session_state.token):
            st.success(f"✅ Already logged in as **{st.session_state.username}**")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("🎨 Go to Artisan Agent", use_container_width=True):
                    st.switch_page("pages/artisan_page.py")
            
            with col2:
                if st.button("🚪 Logout", use_container_width=True):
                    logout_user(st.session_state.token)
                    st.session_state.authenticated = False
                    st.session_state.token = None
                    st.session_state.username = None
                    st.rerun()
            
            return
        else:
            # Token expired, clear session
            st.session_state.authenticated = False
            st.session_state.token = None
            st.session_state.username = None
    
    # Display login form
    st.title("🔐 Prompt2Mesh Login")
    st.markdown("---")
    
    # Check backend status
    backend_online = check_backend_status()
    
    if backend_online:
        st.success("✅ Backend server is online")
    else:
        st.error("❌ Backend server is offline. Please start the backend server first.")
        st.code("python src/backend/backend_server.py", language="bash")
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
                with st.spinner("Authenticating..."):
                    result = login_user(username, password)
                    
                    if result:
                        # Store authentication info in session state
                        st.session_state.authenticated = True
                        st.session_state.token = result["token"]
                        st.session_state.username = result["username"]
                        
                        st.success(f"✅ Welcome, {result['username']}!")
                        time.sleep(1)
                        
                        # Redirect to artisan page
                        st.switch_page("pages/artisan_page.py")
                    else:
                        st.error("❌ Invalid username or password")
    
    # Info section
    st.markdown("---")
    st.info("""
    **Default Credentials:**
    - Username: `root`
    - Password: `root`
    
    *Note: These credentials are stored securely in the PostgreSQL database.*
    """)


if __name__ == "__main__":
    main()
