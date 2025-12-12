"""
Artisan Agent page - Protected by authentication
Enhanced chat interface with AI refinement
"""
import streamlit as st
import requests
import time
import re
from pathlib import Path
from datetime import datetime
import json
import os
import sys

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(parent_dir))

# Add src directory to path for Docker compatibility
src_dir = parent_dir / "src"
if src_dir.exists():
    sys.path.insert(0, str(src_dir))

# Try different import patterns for local vs Docker
try:
    from backend.api_client import BlenderChatAPIClient
    from config import get_backend_url
except ImportError:
    try:
        from src.backend.api_client import BlenderChatAPIClient
        from src.config import get_backend_url
    except ImportError:
        # Fallback for pages subdirectory
        sys.path.insert(0, str(parent_dir / "src" / "backend"))
        sys.path.insert(0, str(parent_dir / "src"))
        from api_client import BlenderChatAPIClient
        from config import get_backend_url

# Backend API configuration
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


def extract_image_from_result(result_text: str) -> tuple[str, str]:
    """Extract base64 image data from result text"""
    pattern = r'\[Image: data:image/(\w+);base64,([A-Za-z0-9+/=]+)\]'
    match = re.search(pattern, result_text)
    
    if match:
        image_format = match.group(1)
        image_data = match.group(2)
        clean_text = re.sub(pattern, '', result_text).strip()
        return clean_text, image_data
    
    return result_text, None


def main():
    """Main Artisan Agent chat interface"""
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
        st.title("🎨 Artisan Agent - AI-Powered 3D Modeling")
    
    with col2:
        st.info(f"👤 {st.session_state.get('username', 'User')}")
    
    with col3:
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.switch_page("login_page.py")
    
    st.markdown("*AI-powered prompt expansion for detailed 3D modeling*")
    st.markdown("---")
    
    # Initialize clients in session state
    if 'client' not in st.session_state:
        st.session_state.client = BlenderChatAPIClient()
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Connection status
        backend_status = st.session_state.client.health_check()
        
        if backend_status:
            st.success("✅ Backend Connected")
            
            if not st.session_state.connected:
                if st.button("🔌 Connect to Blender", use_container_width=True):
                    with st.spinner("Connecting to Blender..."):
                        result = st.session_state.client.connect()
                        if result.get("connected"):
                            st.session_state.connected = True
                            st.success(f"Connected! {result.get('num_tools', 0)} tools available")
                            st.rerun()
                        else:
                            st.error(f"Connection failed: {result.get('error', 'Unknown error')}")
            else:
                st.success("✅ Blender Connected")
                if st.button("🔌 Disconnect", use_container_width=True):
                    st.session_state.client.disconnect()
                    st.session_state.connected = False
                    st.rerun()
        else:
            st.error("❌ Backend Offline")
            st.info("Start backend: `python src/backend/backend_server.py`")
        
        st.divider()
        
        # Prompt refinement toggle
        st.subheader("🧠 AI Prompt Refinement")
        use_refinement = st.toggle(
            "Enable Prompt Expansion",
            value=True,
            help="AI will expand simple prompts into detailed 3D modeling descriptions"
        )
        
        if use_refinement:
            detail_level = st.selectbox(
                "Detail Level",
                options=["as-is", "concise", "moderate", "comprehensive"],
                index=3,  # Default to comprehensive
                help="Control how detailed the AI expansion should be"
            )
            
            level_info = {
                "as-is": "📝 Use your prompt exactly as written - no AI refinement or expansion",
                "concise": "💡 Basic structure, key features, and materials (300-500 words)",
                "moderate": "💡 Balanced detail with structure, components, materials, and key specs (500-1000 words)",
                "comprehensive": "💡 Exhaustive detail with all specifications, measurements, and rendering info (1000+ words)"
            }
            st.info(level_info[detail_level])
        else:
            detail_level = "comprehensive"  # Default when refinement is off
        
        st.divider()
        
        # Refinement steps control
        st.subheader("🔄 Quality Refinement")
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
        
        # Save chat as Artisan prompt
        st.subheader("💾 Save for Artisan Agent")
        
        # Check if there are any messages with refinement
        has_refined_prompts = any(
            msg.get("refinement_info") and msg.get("role") == "user" 
            for msg in st.session_state.messages
        )
        
        if has_refined_prompts:
            st.info("💡 Save your refined prompts for batch execution in the Artisan Agent")
            
            # Select which prompt to save
            refined_messages = [
                (i, msg) for i, msg in enumerate(st.session_state.messages)
                if msg.get("refinement_info") and msg.get("role") == "user"
            ]
            
            if len(refined_messages) > 0:
                # Show dropdown of available prompts
                prompt_options = {}
                for idx, (i, msg) in enumerate(refined_messages, 1):
                    original = msg["content"][:50] + ("..." if len(msg["content"]) > 50 else "")
                    prompt_options[f"Prompt {idx}: {original}"] = i
                
                selected_prompt_label = st.selectbox(
                    "Select Prompt to Save",
                    options=list(prompt_options.keys()),
                    help="Choose which refined prompt to save for Artisan Agent"
                )
                
                selected_idx = prompt_options[selected_prompt_label]
                selected_msg = st.session_state.messages[selected_idx]
                
                # Show preview
                with st.expander("Preview Selected Prompt", expanded=False):
                    st.markdown(f"**Original:** {selected_msg['content']}")
                    if selected_msg.get("refinement_info"):
                        refined_text = selected_msg["refinement_info"].get("refined_prompt", "")
                        if refined_text:
                            preview_len = min(300, len(refined_text))
                            st.markdown(f"**Refined:** {refined_text[:preview_len]}{'...' if len(refined_text) > preview_len else ''}")
                        
                        st.markdown(f"**Detail Level:** {selected_msg['refinement_info'].get('detail_level', 'N/A')}")
                        st.markdown(f"**Was Already Detailed:** {'Yes' if selected_msg['refinement_info'].get('was_detailed') else 'No'}")
                
                # Save button
                if st.button("💾 Save as JSON for Artisan", use_container_width=True):
                    try:
                        # Get the refinement info
                        refinement_info = selected_msg.get("refinement_info", {})
                        
                        # Get the refined prompt text (stored in refinement_info)
                        refined_prompt_text = refinement_info.get("refined_prompt", selected_msg["content"])
                        
                        # Create JSON structure
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        original_short = selected_msg["content"][:50].replace(" ", "_").replace("/", "_").replace("\\", "_")
                        filename = f"{timestamp}_{original_short}.json"
                        
                        prompt_data = {
                            "timestamp": datetime.now().isoformat(),
                            "original_prompt": selected_msg["content"],
                            "refined_prompt": refined_prompt_text,
                            "is_detailed": refinement_info.get("was_detailed", True),
                            "detail_level": refinement_info.get("detail_level", detail_level),
                            "reasoning_steps": refinement_info.get("reasoning_steps", [])
                        }
                        
                        # Save JSON file
                        json_dir = Path("data/prompts/json")
                        json_dir.mkdir(parents=True, exist_ok=True)
                        json_path = json_dir / filename
                        
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(prompt_data, f, indent=2, ensure_ascii=False)
                        
                        # Save text file (just the refined prompt text)
                        text_dir = Path("data/prompts/text")
                        text_dir.mkdir(parents=True, exist_ok=True)
                        text_filename = filename.replace('.json', '.txt')
                        text_path = text_dir / text_filename
                        
                        with open(text_path, 'w', encoding='utf-8') as f:
                            f.write(refined_prompt_text)
                        
                        st.success(f"✅ Saved JSON: {json_path}")
                        st.success(f"✅ Saved Text: {text_path}")
                        st.info("🎯 Go to **Batch Artisan Agent** page to execute this prompt!")
                        
                    except Exception as e:
                        st.error(f"❌ Failed to save: {e}")
        else:
            st.info("💡 Chat with refinement enabled to create prompts for the Artisan Agent")
        
        st.divider()
        
        # Clear chat
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Show conversation history
        if st.session_state.connected:
            with st.expander("📜 Conversation History"):
                history = st.session_state.client.get_history()
                st.json(history)
    
    # Main chat area
    st.header("💬 Chat")
    
    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Display image if present
            if "image" in message and message["image"]:
                st.image(f"data:image/png;base64,{message['image']}", caption="Viewport Screenshot")
            
            # Display tool calls in expander
            if "tool_calls" in message and message["tool_calls"]:
                with st.expander(f"🔧 Tool Executions ({len(message['tool_calls'])})"):
                    for tool_call in message["tool_calls"]:
                        st.markdown(f"**Tool:** `{tool_call.get('tool_name')}`")
                        st.markdown(f"**Success:** {'✅' if tool_call.get('success') else '❌'}")
                        
                        # Show arguments
                        if tool_call.get('arguments'):
                            st.markdown("**Arguments:**")
                            st.json(tool_call['arguments'])
                        
                        # Show result
                        result_text = tool_call.get('result', '')
                        clean_result, _ = extract_image_from_result(result_text)
                        st.markdown("**Result:**")
                        st.code(clean_result, language=None)
                        st.divider()
            
            # Display refinement info if present
            if "refinement_info" in message:
                with st.expander("🧠 AI Prompt Refinement"):
                    info = message["refinement_info"]
                    st.markdown(f"**Original:** {info['original']}")
                    st.markdown(f"**Was Detailed:** {'Yes ✅' if info['was_detailed'] else 'No, expanded ➡️'}")
                    
                    if info.get('reasoning_steps'):
                        st.markdown("**Reasoning Steps:**")
                        for i, step in enumerate(info['reasoning_steps'], 1):
                            st.text(f"{i}. {step}")
    
    # Chat input
    if prompt := st.chat_input("Describe what you want to create in Blender...", disabled=not st.session_state.connected):
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Refine prompt if enabled
        refined_prompt = prompt
        refinement_info = None
        
        # Check if refinement should be applied
        should_refine = use_refinement and detail_level != "as-is"
        
        if should_refine:
            with st.spinner("🧠 AI is analyzing and expanding your prompt..."):
                try:
                    # Call backend API for prompt refinement
                    refinement_result = st.session_state.client.refine_prompt(
                        prompt=prompt,
                        thread_id=st.session_state.client._session_id,
                        detail_level=detail_level
                    )
                    
                    refined_prompt = refinement_result["refined_prompt"]
                    refinement_info = {
                        "original": prompt,
                        "refined_prompt": refined_prompt,  # Store the actual refined prompt
                        "was_detailed": refinement_result["is_detailed"],
                        "reasoning_steps": refinement_result["reasoning_steps"],
                        "detail_level": detail_level
                    }
                    
                    # Show refinement notification
                    if not refinement_result["is_detailed"]:
                        st.info("🧠 AI expanded your prompt with detailed specifications")
                
                except Exception as e:
                    st.warning(f"Prompt refinement failed, using original: {e}")
                    refined_prompt = prompt
        
        # Always create refinement_info (even if no refinement applied)
        if refinement_info is None:
            # Use prompt as-is (either "as-is" selected or refinement disabled)
            reason = "as-is" if detail_level == "as-is" else "refinement disabled"
            st.info(f"📝 Using your prompt as-is ({reason})")
            refinement_info = {
                "original": prompt,
                "refined_prompt": prompt,
                "was_detailed": True,
                "reasoning_steps": [f"Used prompt as-is ({reason})"],
                "detail_level": detail_level
            }
        
        # Add user message with refinement info
        st.session_state.messages.append({
            "role": "user",
            "content": prompt,
            "refinement_info": refinement_info
        })
        
        # Auto-save prompt to JSON and TXT files if refinement_info exists
        if refinement_info:
            try:
                refined_prompt_text = refinement_info.get("refined_prompt", prompt)
                
                # Create JSON structure
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                original_short = prompt[:50].replace(" ", "_").replace("/", "_").replace("\\", "_")
                filename = f"{timestamp}_{original_short}.json"
                
                prompt_data = {
                    "timestamp": datetime.now().isoformat(),
                    "original_prompt": prompt,
                    "refined_prompt": refined_prompt_text,
                    "is_detailed": refinement_info.get("was_detailed", True),
                    "detail_level": refinement_info.get("detail_level", detail_level),
                    "reasoning_steps": refinement_info.get("reasoning_steps", []),
                    "enable_refinement_steps": enable_refinement_steps
                }
                
                # Save JSON file
                json_dir = Path("data/prompts/json")
                json_dir.mkdir(parents=True, exist_ok=True)
                json_path = json_dir / filename
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(prompt_data, f, indent=2, ensure_ascii=False)
                
                # Save text file (just the refined prompt text)
                text_dir = Path("data/prompts/text")
                text_dir.mkdir(parents=True, exist_ok=True)
                text_filename = filename.replace('.json', '.txt')
                text_path = text_dir / text_filename
                
                with open(text_path, 'w', encoding='utf-8') as f:
                    f.write(refined_prompt_text)
                
                st.success(f"✅ Auto-saved: {json_path.name}")
                
            except Exception as e:
                st.warning(f"⚠️ Auto-save failed: {e}")
        
        # Send to Blender agent
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            with st.spinner("🤖 Processing with Blender..."):
                try:
                    response = st.session_state.client.chat(refined_prompt)
                    
                    # Combine responses
                    full_response = "\n\n".join(response.get("responses", ["No response"]))
                    tool_calls = response.get("tool_calls", [])
                    
                    # Extract image from any tool call
                    image_data = None
                    for tool_call in tool_calls:
                        if tool_call.get("image_data"):
                            image_data = tool_call["image_data"]
                            break
                    
                    # Display response
                    message_placeholder.markdown(full_response)
                    
                    # Display image if captured
                    if image_data:
                        st.image(f"data:image/png;base64,{image_data}", caption="Viewport Screenshot")
                    
                    # Display tool calls
                    if tool_calls:
                        with st.expander(f"🔧 Tool Executions ({len(tool_calls)})"):
                            for tool_call in tool_calls:
                                st.markdown(f"**Tool:** `{tool_call.get('tool_name')}`")
                                st.markdown(f"**Success:** {'✅' if tool_call.get('success') else '❌'}")
                                
                                if tool_call.get('arguments'):
                                    st.markdown("**Arguments:**")
                                    st.json(tool_call['arguments'])
                                
                                result_text = tool_call.get('result', '')
                                clean_result, _ = extract_image_from_result(result_text)
                                st.markdown("**Result:**")
                                st.code(clean_result, language=None)
                                st.divider()
                    
                    # Show refinement info if present
                    if refinement_info:
                        with st.expander("🧠 AI Prompt Refinement"):
                            st.markdown(f"**Original:** {refinement_info['original']}")
                            st.markdown(f"**Was Detailed:** {'Yes ✅' if refinement_info['was_detailed'] else 'No, expanded ➡️'}")
                            
                            if refinement_info.get('reasoning_steps'):
                                st.markdown("**Reasoning Steps:**")
                                for i, step in enumerate(refinement_info['reasoning_steps'], 1):
                                    st.text(f"{i}. {step}")
                    
                    # Add to messages
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_response,
                        "tool_calls": tool_calls,
                        "image": image_data,
                        "refinement_info": refinement_info
                    })
                
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    message_placeholder.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": error_msg
                    })


if __name__ == "__main__":
    main()
