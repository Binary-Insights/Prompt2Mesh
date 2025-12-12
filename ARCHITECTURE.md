# Blender Chat - FastAPI + Streamlit Architecture

This application has been refactored into a **backend-frontend architecture** for better separation of concerns and scalability.

## Architecture Overview

```
┌─────────────────────┐
│  Streamlit Frontend │  (streamlit_blender_chat.py)
│   Port: 8501        │
└──────────┬──────────┘
           │ HTTP/REST
           ▼
┌─────────────────────┐
│  FastAPI Backend    │  (backend_server.py)
│   Port: 8000        │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  BlenderChatAgent   │  (blender_agent.py)
│                     │
└──────────┬──────────┘
           │ MCP
           ▼
┌─────────────────────┐
│  Blender (via MCP)  │
│   Port: 9876        │
└─────────────────────┘
```

## Files Structure

### Core Files

- **`blender_agent.py`** - Core agent class that manages MCP connection and Claude API
- **`backend_server.py`** - FastAPI REST API server 
- **`api_client.py`** - API client helper for frontend to communicate with backend
- **`streamlit_blender_chat.py`** - Streamlit UI (frontend only)

### Legacy Files

- **`blender_chat.py`** - Original monolithic CLI version (still works independently)

## Installation

Install the required dependencies:

```bash
pip install fastapi uvicorn[standard] requests streamlit anthropic mcp
```

Or if you have a requirements file, update it with:
```
fastapi
uvicorn[standard]
requests
streamlit
anthropic
mcp
```

## Running the Application

### Step 1: Start the Backend Server

From the **project root directory**:

**Option 1 - Using Python module syntax:**
```bash
python -m src.backend.backend_server
```

**Option 2 - Using uvicorn directly:**
```bash
uvicorn src.backend.backend_server:app --reload --port 8000
```

**Option 3 - Direct execution:**
```bash
python src/backend/backend_server.py
```

The backend will be available at: `http://localhost:8000`

### Step 2: Start the Streamlit Frontend

From the **project root directory**:
```bash
streamlit run src/frontend/streamlit_blender_chat.py
```

The frontend will open in your browser at: `http://localhost:8501`

### Step 3: Connect to Blender

1. Make sure Blender is running with the MCP addon
2. Click "Connect to Blender" in the Streamlit sidebar
3. Start chatting!

## API Endpoints

The FastAPI backend provides the following REST endpoints:

- **GET** `/` - API information
- **POST** `/connect` - Connect to Blender MCP server
- **POST** `/disconnect` - Disconnect from Blender
- **GET** `/status` - Get connection status
- **POST** `/chat` - Send a chat message
  ```json
  {
    "message": "Create a sphere at the origin"
  }
  ```
- **GET** `/history` - Get conversation history
- **POST** `/clear-history` - Clear conversation history

### API Documentation

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Environment Variables

Create a `.env` file in the project root:

```env
ANTHROPIC_API_KEY=your-api-key-here
```

## Advantages of This Architecture

### 1. **Separation of Concerns**
   - Frontend (Streamlit) handles only UI/UX
   - Backend (FastAPI) handles business logic and AI
   - Agent (Class) manages MCP and Claude connections

### 2. **Scalability**
   - Multiple frontends can connect to the same backend
   - Backend can be deployed independently
   - Easier to add features without UI changes

### 3. **Testing**
   - Backend API can be tested independently with tools like Postman
   - Frontend can be tested with mock API responses
   - Agent logic is isolated and unit-testable

### 4. **Deployment**
   - Backend and frontend can be deployed on different servers
   - Can use Docker containers for each component
   - Better resource management

### 5. **No Event Loop Issues**
   - Backend manages async operations properly
   - Frontend makes simple HTTP requests
   - Cleaner code with fewer async/await complexities

## Development

### Testing the Backend

```bash
# Test with curl
curl http://localhost:8000/

# Connect to Blender
curl -X POST http://localhost:8000/connect

# Send a chat message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a cube"}'

# Get status
curl http://localhost:8000/status
```

### Testing with Python

```python
from api_client import BlenderChatAPIClient

client = BlenderChatAPIClient("http://localhost:8000")

# Connect
result = client.connect()
print(result)

# Chat
response = client.chat("Create a sphere")
print(response)

# Disconnect
client.disconnect()
```

## Troubleshooting

### Backend not connecting
- Ensure ANTHROPIC_API_KEY is set
- Check that Blender MCP server is running
- Verify port 8000 is not in use

### Frontend can't reach backend
- Check backend is running on port 8000
- Look for "Backend Server Running" in Streamlit sidebar
- Check console for error messages

### Connection issues
- Make sure Blender addon is installed and active
- Verify Blender is listening on port 9876
- Check firewall settings

## Next Steps

Potential enhancements:
- Add authentication/authorization
- Implement WebSocket for real-time updates
- Add database for conversation persistence
- Deploy backend to cloud (AWS, GCP, Azure)
- Create additional frontends (CLI, web app, mobile)
- Add caching layer for better performance
