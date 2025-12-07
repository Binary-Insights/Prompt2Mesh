# Prompt2Mesh
Final Project - Control Blender with Natural Language

## 🚀 Quick Start (Multi-User System)

### 1. Start the Backend

```powershell
cd docker
docker-compose up -d
```

### 2. Access the Web Interface

Open your browser: **http://localhost:8501**

### 3. Create Your Account

1. Click **"Sign Up"**
2. Enter username and password
3. Click **"Create Account"**

### 4. Login

1. Enter your credentials
2. Click **"Login"**
3. Wait 5-10 seconds while your personal Blender instance is created
4. You'll see your **Blender UI URL** (e.g., `http://localhost:13000`)

### 5. Enable MCP Addon (One-Time Setup)

**The addon is pre-installed!** You just need to enable it:

1. Click on your Blender UI URL to open Blender
2. In Blender: **Edit → Preferences → Add-ons**
3. Search for **"MCP"** or **"Blender MCP Server"**
4. Check the box to enable it
5. Close preferences

✅ The addon will start automatically on port 9876

### 6. Connect and Chat

1. Return to the chat interface
2. Click **"Connect to Blender"**
3. Start creating! Try: *"Create a Christmas tree"*

## ✨ Features

- **Multi-User Support**: Each user gets their own isolated Blender instance
- **Persistent Workspace**: Your Blender scenes are saved between sessions
- **AI-Powered**: Uses Claude Sonnet 3.5 with specialized Blender agents
- **No Interference**: Multiple users can work simultaneously without conflicts

## 🏗️ Architecture

### Multi-User Container System

- **Backend (FastAPI)**: JWT authentication, session management, Docker orchestration
- **Database (PostgreSQL)**: User accounts and session tracking
- **Per-User Containers**: Each user gets an isolated Blender instance
- **Port Allocation**: Dynamic port assignment (MCP: 10000+, UI: 13000+)
- **Frontend (Streamlit)**: Web-based chat interface

### Components

- `src/backend/` - FastAPI server with authentication
- `src/frontend/` - Streamlit web interface
- `src/addon/` - Blender MCP addon
- `src/blender/` - Blender agent (Anthropic integration)
- `src/artisan_agent/` - Autonomous 3D modeling agent
- `src/refinement_agent/` - Prompt refinement system
- `docker/` - Docker configuration

## 📚 Documentation

- `QUICKSTART.md` - Step-by-step setup guide
- `ARCHITECTURE.md` - System design overview
- `AUTH_SETUP.md` - Authentication system details
- `MCP_ADDON_STATUS.md` - Current status and workarounds
- `src/artisan_agent/README.md` - Artisan agent documentation

## 🔧 Advanced Usage

### Artisan Agent - Autonomous 3D Modeling

An intelligent agent that reads requirements and autonomously builds 3D models in Blender.

**Features:**
- 📖 Reads detailed requirements from JSON files
- 🧠 Plans sequential modeling steps using Claude Sonnet 3.5
- 🔧 Executes Blender MCP tools automatically
- 📸 Captures viewport screenshots for visual feedback
- 🔄 Iterates until modeling is complete
- 📊 Full LangSmith tracing for debugging

See [Artisan Agent README](src/artisan_agent/README.md) for detailed documentation.

Expands simple user prompts into detailed 3D modeling specifications.

**Features:**
- Analyzes user intent
- Generates comprehensive technical specifications
- Includes dimensions, materials, textures, and rendering details
- Multiple detail levels (concise/moderate/comprehensive)
- Saves requirements as JSON for Artisan Agent

**Usage:**

```bash
# Backend API
uvicorn src.backend.backend_server:app --reload

# Frontend
streamlit run src/frontend/streamlit_blender_chat_with_refinement.py
```

See [Prompt Refinement README](src/refinement_agent/) for more details.

