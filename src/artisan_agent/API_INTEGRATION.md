# Artisan Agent API Integration

## Overview

The Artisan Agent has been integrated into the Backend Server as a REST API, allowing the Streamlit UI and other clients to run modeling tasks without directly importing the agent code.

## Architecture

```
┌─────────────────┐         HTTP API          ┌─────────────────┐
│                 │ ◄────────────────────────► │                 │
│  Streamlit UI   │    Start/Poll Tasks       │ Backend Server  │
│  (Frontend)     │                            │   (FastAPI)     │
└─────────────────┘                            └────────┬────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │ Artisan Agent   │
                                               │ (Background)    │
                                               └────────┬────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │  Blender MCP    │
                                               │    Server       │
                                               └─────────────────┘
```

## API Endpoints

### 1. Start Modeling Task

**POST** `/artisan/model`

Start a new 3D modeling task.

**Request:**
```json
{
  "requirement_file": "data/prompts/json/20251127_135557_Could_you_model_a_ch.json",
  "use_resume": true
}
```

**Response:**
```json
{
  "task_id": "a3f8c9e1",
  "status": "started",
  "message": "Modeling task started with ID: a3f8c9e1"
}
```

### 2. Get Task Status

**GET** `/artisan/status/{task_id}`

Poll the status of a running task.

**Response (Running):**
```json
{
  "task_id": "a3f8c9e1",
  "status": "running",
  "session_id": "f9170ff8a647e579",
  "steps_executed": 5,
  "screenshots_captured": 3,
  "screenshot_directory": "data/blender/screenshots/f9170ff8a647e579",
  "success": false,
  "error": null,
  "tool_results": [...]
}
```

**Response (Completed):**
```json
{
  "task_id": "a3f8c9e1",
  "status": "completed",
  "session_id": "f9170ff8a647e579",
  "steps_executed": 10,
  "screenshots_captured": 10,
  "screenshot_directory": "data/blender/screenshots/f9170ff8a647e579",
  "success": true,
  "error": null,
  "tool_results": [
    {
      "success": true,
      "tool_name": "execute_blender_code",
      "arguments": {...},
      "result": "..."
    }
  ]
}
```

### 3. List All Tasks

**GET** `/artisan/tasks`

Get a list of all modeling tasks (active and completed).

**Response:**
```json
{
  "tasks": [
    {
      "task_id": "a3f8c9e1",
      "status": "completed",
      "requirement_file": "data/prompts/json/tree.json",
      "use_resume": true
    },
    {
      "task_id": "b4e7d2f8",
      "status": "running",
      "requirement_file": "data/prompts/json/chair.json",
      "use_resume": false
    }
  ],
  "total": 2
}
```

## Task Statuses

- **`initializing`**: Agent is being created and initialized
- **`running`**: Task is actively executing modeling steps
- **`completed`**: Task finished successfully
- **`failed`**: Task encountered an error

## Usage

### Starting the Backend Server

```bash
# Start the backend server
python src/backend/backend_server.py

# Server will run on http://localhost:8000
```

### Using the Streamlit UI

```bash
# Start Streamlit UI
streamlit run src/artisan_agent/streamlit_artisan.py

# UI will automatically connect to http://localhost:8000
```

### Python Client Example

```python
import requests
import time

# Start a modeling task
response = requests.post(
    "http://localhost:8000/artisan/model",
    json={
        "requirement_file": "data/prompts/json/my_model.json",
        "use_resume": True
    }
)
task_id = response.json()["task_id"]
print(f"Task started: {task_id}")

# Poll for completion
while True:
    status = requests.get(f"http://localhost:8000/artisan/status/{task_id}").json()
    
    print(f"Status: {status['status']} | Steps: {status['steps_executed']}")
    
    if status["status"] == "completed":
        print(f"✅ Success! Screenshots: {status['screenshot_directory']}")
        break
    elif status["status"] == "failed":
        print(f"❌ Failed: {status['error']}")
        break
    
    time.sleep(2)  # Poll every 2 seconds
```

### cURL Examples

**Start Task:**
```bash
curl -X POST http://localhost:8000/artisan/model \
  -H "Content-Type: application/json" \
  -d '{
    "requirement_file": "data/prompts/json/tree.json",
    "use_resume": true
  }'
```

**Check Status:**
```bash
curl http://localhost:8000/artisan/status/a3f8c9e1
```

**List Tasks:**
```bash
curl http://localhost:8000/artisan/tasks
```

## Benefits of API Architecture

### 1. **Separation of Concerns**
- Frontend (Streamlit) handles UI/UX
- Backend (FastAPI) handles business logic and agent execution
- Easy to swap frontend or add new clients

### 2. **Background Processing**
- Tasks run asynchronously in background
- UI doesn't freeze during long-running operations
- Can start multiple tasks concurrently

### 3. **Scalability**
- Backend can be deployed on separate server
- Multiple frontends can connect to same backend
- Easy to add load balancing, queuing, etc.

### 4. **State Management**
- Backend tracks all tasks in `artisan_tasks` dictionary
- Can query task history and status
- Resume interrupted tasks by checking status

### 5. **Error Isolation**
- Agent errors don't crash the UI
- Backend handles cleanup gracefully
- Clear error reporting via API responses

## Advanced Usage

### Webhook Notifications (Future)

```python
# Start task with webhook
response = requests.post(
    "http://localhost:8000/artisan/model",
    json={
        "requirement_file": "data/prompts/json/tree.json",
        "use_resume": true,
        "webhook_url": "https://myapp.com/webhook"  # Future feature
    }
)
```

### Task Prioritization (Future)

```python
# High-priority task
response = requests.post(
    "http://localhost:8000/artisan/model",
    json={
        "requirement_file": "data/prompts/json/urgent.json",
        "use_resume": true,
        "priority": "high"  # Future feature
    }
)
```

### Batch Processing (Future)

```python
# Process multiple models
response = requests.post(
    "http://localhost:8000/artisan/batch",
    json={
        "requirement_files": [
            "data/prompts/json/model1.json",
            "data/prompts/json/model2.json",
            "data/prompts/json/model3.json"
        ],
        "use_resume": true
    }
)
```

## Monitoring

### Health Check

```bash
curl http://localhost:8000/
```

**Response:**
```json
{
  "message": "Blender Chat API",
  "version": "1.0.0",
  "endpoints": {...},
  "refinement_agent_available": true,
  "artisan_agent_available": true
}
```

### Active Tasks

```bash
# Check how many tasks are running
curl http://localhost:8000/artisan/tasks | jq '.total'
```

## Troubleshooting

### Backend Not Running

**Symptom:** `Connection refused` errors in Streamlit

**Solution:**
```bash
# Start backend server
python src/backend/backend_server.py
```

### Task Stuck in "Running"

**Symptom:** Task shows "running" but no progress

**Solution:**
1. Check backend server logs for errors
2. Check Blender MCP server is running
3. Restart backend server if needed

### High Memory Usage

**Symptom:** Backend consuming excessive RAM

**Solution:**
- Tasks store full results in memory
- Restart backend periodically to clear old tasks
- Future: Add task cleanup endpoint

## Migration from Direct Import

### Before (Direct Import)

```python
from src.artisan_agent import ArtisanAgent

agent = ArtisanAgent()
await agent.initialize()
results = await agent.run("file.json")
```

### After (API Call)

```python
import requests

# Start task
response = requests.post("http://localhost:8000/artisan/model", json={
    "requirement_file": "file.json"
})
task_id = response.json()["task_id"]

# Poll for results
status = requests.get(f"http://localhost:8000/artisan/status/{task_id}").json()
```

## Security Considerations

### Current (Development)

- No authentication required
- Accepts any file path
- No rate limiting

### Production (Recommended)

```python
# Add API key authentication
headers = {"X-API-Key": "your-secret-key"}
response = requests.post(url, json=data, headers=headers)

# Validate file paths (server-side)
# Add rate limiting
# Use HTTPS
# Implement user permissions
```

---

**Last Updated**: November 27, 2025  
**Version**: 1.0.0  
**Status**: Production Ready
