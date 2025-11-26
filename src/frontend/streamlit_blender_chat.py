#!/usr/bin/env python3
"""
AI-Powered Blender Chat - Streamlit Frontend
Communicates with FastAPI backend for Blender control
"""
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import json
import streamlit as st
import requests
import base64
from io import BytesIO
from PIL import Image as PILImage
from api_client import BlenderChatAPIClient

# Page config
st.set_page_config(
    page_title="AI-Powered Blender Chat",
    page_icon="🎨",
    layout="wide"
)

# Initialize API client with configurable backend URL
import os
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
api_client = BlenderChatAPIClient(BACKEND_URL)

# Initialize session state
if 'connected' not in st.session_state:
    st.session_state.connected = False
    st.session_state.messages = []
    st.session_state.tool_history = []
    st.session_state.num_tools = 0

def extract_image_from_result(result_text):
    """Extract base64 image data from result text if present"""
    try:
        # Look for base64 image data in the result
        if "data:image" in result_text:
            # Extract the base64 data
            start = result_text.find("data:image")
            end = result_text.find('"', start)
            if end == -1:
                end = len(result_text)
            data_url = result_text[start:end]
            
            # Parse the data URL
            if "base64," in data_url:
                base64_data = data_url.split("base64,")[1]
                image_data = base64.b64decode(base64_data)
                return PILImage.open(BytesIO(image_data))
    except Exception:
        pass
    return None

# Main UI
st.title("🎨 AI-Powered Blender Chat")
st.markdown("Use natural language to create 3D scenes in Blender")

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Display backend URL
    st.caption(f"Backend: `{BACKEND_URL}`")
    
    # Backend status check
    backend_running = api_client.health_check()
    if backend_running:
        st.success("✓ Backend Server Running")
    else:
        st.error("❌ Backend Server Not Running")
        st.info(f"Start backend with: `python src/backend/backend_server.py`")
        st.warning("If running from WSL, try: `BACKEND_URL=http://127.0.0.1:8000 streamlit run ...`")
    
    # Connection status
    st.header("🔌 Connection")
    
    if not st.session_state.connected:
        if st.button("Connect to Blender", type="primary", disabled=not backend_running):
            with st.spinner("Connecting to Blender MCP server..."):
                try:
                    result = api_client.connect()
                    if result.get("connected"):
                        st.session_state.connected = True
                        st.session_state.num_tools = result.get("num_tools", 0)
                        st.success(f"✓ Connected! Loaded {st.session_state.num_tools} tools")
                        st.rerun()
                    else:
                        st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"Connection failed: {str(e)}")
    else:
        st.success("✓ Connected to Blender")
        if st.button("Disconnect"):
            try:
                api_client.disconnect()
                st.session_state.connected = False
                st.session_state.messages = []
                st.session_state.tool_history = []
                st.session_state.num_tools = 0
                st.rerun()
            except requests.exceptions.RequestException as e:
                st.error(f"Disconnect failed: {str(e)}")
    
    # Examples
    st.header("💡 Examples")
    st.markdown("""
    - Create a sphere at the origin
    - Add a camera looking at the center
    - Make a scene with 3 cubes
    - Download a chair model from PolyHaven
    - Set up studio lighting
    """)
    
    # Tool history
    if st.session_state.tool_history:
        st.header("🔧 Tool History")
        for i, tool_call in enumerate(reversed(st.session_state.tool_history[-5:])):
            with st.expander(f"{tool_call['tool_name']}", expanded=False):
                if tool_call.get('arguments'):
                    st.code(json.dumps(tool_call['arguments'], indent=2), language="json")
                status = "✓" if tool_call['success'] else "✗"
                st.caption(f"{status} {tool_call['result'][:100]}...")

# Main chat area
if not st.session_state.connected:
    st.info("👈 Please connect to Blender to start chatting")
else:
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display tool calls if present
            if "tool_calls" in message and message["tool_calls"]:
                with st.expander(f"🔧 Executed {len(message['tool_calls'])} tool(s)", expanded=False):
                    for tool_call in message["tool_calls"]:
                        status_icon = "✓" if tool_call['success'] else "✗"
                        st.markdown(f"**{status_icon} {tool_call['tool_name']}**")
                        if tool_call.get('arguments'):
                            st.code(json.dumps(tool_call['arguments'], indent=2), language="json")
                        
                        # Check if result contains an image
                        if tool_call.get('success') and tool_call['tool_name'] == 'get_viewport_screenshot':
                            img = extract_image_from_result(tool_call['result'])
                            if img:
                                st.image(img, caption="Blender Viewport Screenshot", use_container_width=True)
                            else:
                                st.caption(tool_call['result'][:200])
                        else:
                            st.caption(tool_call['result'][:200])
    
    # Chat input
    if prompt := st.chat_input("Ask me to create something in Blender..."):
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get assistant response
        with st.chat_message("assistant"):
            with st.spinner("Claude is thinking..."):
                try:
                    # Send chat request to backend
                    result = api_client.chat(prompt)
                    
                    # Combine all responses
                    full_response = "\n\n".join(result["responses"]) if result.get("responses") else "I've executed your request."
                    
                    st.markdown(full_response)
                    
                    # Display screenshots prominently if captured
                    for tool_call in result.get("tool_calls", []):
                        if tool_call.get('success') and tool_call['tool_name'] == 'get_viewport_screenshot':
                            img = extract_image_from_result(tool_call['result'])
                            if img:
                                st.image(img, caption="📸 Blender Viewport", use_container_width=True)
                    
                    # Add to message history
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "tool_calls": result.get("tool_calls", [])
                    })
                    
                    # Add to tool history
                    st.session_state.tool_history.extend(result.get("tool_calls", []))
                    
                    # Display tool calls
                    if result.get("tool_calls"):
                        with st.expander(f"🔧 Executed {len(result['tool_calls'])} tool(s)", expanded=True):
                            for tool_call in result["tool_calls"]:
                                status_icon = "✓" if tool_call['success'] else "✗"
                                st.markdown(f"**{status_icon} {tool_call['tool_name']}**")
                                if tool_call.get('arguments'):
                                    st.code(json.dumps(tool_call['arguments'], indent=2), language="json")
                                
                                # Check if result contains an image (for screenshots)
                                if tool_call.get('success') and tool_call['tool_name'] == 'get_viewport_screenshot':
                                    img = extract_image_from_result(tool_call['result'])
                                    if img:
                                        st.image(img, caption="Blender Viewport Screenshot", use_container_width=True)
                                    else:
                                        st.caption(tool_call['result'][:200])
                                else:
                                    st.caption(tool_call['result'][:200])
                
                except requests.exceptions.RequestException as e:
                    st.error(f"Error: {str(e)}")
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": f"Sorry, I encountered an error: {str(e)}"
                    })

# Footer
st.markdown("---")
st.caption("Built with Streamlit, FastAPI, Claude AI, and MCP | Connect to Blender to start creating")
