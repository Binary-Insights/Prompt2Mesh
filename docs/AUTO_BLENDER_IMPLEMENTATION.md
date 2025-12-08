# Automatic Blender Instance Creation - Implementation Summary

## What Was Changed

### 1. Backend (`src/backend/backend_server.py`)

**LoginResponse Model - Added Blender session fields:**
```python
class LoginResponse(BaseModel):
    # ... existing fields ...
    mcp_port: Optional[int] = None
    blender_ui_port: Optional[int] = None
    blender_ui_url: Optional[str] = None
```

**Login Endpoint - Returns Blender session info:**
```python
return LoginResponse(
    success=True,
    token=result["token"],
    user_id=result["user_id"],
    username=result["username"],
    # ... 
    mcp_port=user_session.mcp_port,
    blender_ui_port=user_session.blender_ui_port,
    blender_ui_url=f"http://localhost:{user_session.blender_ui_port}"
)
```

### 2. Frontend (`src/frontend/login_page.py`)

**Session State - Added Blender info storage:**
```python
st.session_state.user_id = result.get("user_id")
st.session_state.blender_ui_url = result.get("blender_ui_url")
st.session_state.mcp_port = result.get("mcp_port")
st.session_state.blender_ui_port = result.get("blender_ui_port")
```

**Login Success - Shows Blender UI link:**
```python
if result.get("blender_ui_url"):
    st.info(f"🎨 Your Blender instance: {result['blender_ui_url']}")
    st.markdown(f"**[🚀 Open Blender UI]({result['blender_ui_url']})**")
    st.caption("Click the link above to open your Blender interface")
```

## How It Works Now

### User Flow:
1. **User logs in** → Backend authenticates
2. **Backend creates Docker container** automatically
   - Container name: `blender-{username}-{user_id}`
   - Assigns unique ports (MCP: 10000+, UI: 13000+)
3. **Backend returns Blender UI URL** in login response
4. **Frontend displays clickable link** to Blender UI
5. **User clicks link** → Opens Blender in new browser tab

### Example Login Response:
```json
{
  "success": true,
  "token": "eyJhbGci...",
  "user_id": 4,
  "username": "alice",
  "mcp_port": 10000,
  "blender_ui_port": 13000,
  "blender_ui_url": "http://localhost:13000"
}
```

## Testing

### Run the automatic test:
```bash
python test_auto_blender.py
```

This test will:
1. Create/login a user
2. Verify Blender container is created
3. Check if UI is accessible
4. Automatically open Blender UI in browser

### Manual test via frontend:
1. Start services: `cd docker && docker-compose up -d`
2. Open Streamlit: `http://localhost:8501`
3. Login with any user
4. See Blender UI link appear
5. Click to open Blender

## Troubleshooting

### "Session manager not available"
- Backend container needs rebuild: `docker-compose build --no-cache backend`
- Or backend not starting properly: `docker logs prompt2mesh-backend`

### Container not created
- Check Docker is running: `docker ps`
- Check backend has Docker access: Backend needs `/var/run/docker.sock` mounted
- Check logs: `docker logs prompt2mesh-backend`

### UI link doesn't work
- Container may still be starting (wait 10-15 seconds)
- Check container status: `docker ps | grep blender-`
- Check container logs: `docker logs blender-{username}-{id}`

## Next Steps

To fully integrate with the artisan agent:
1. Update artisan_page.py to use `st.session_state.mcp_port`
2. Pass user's MCP port when connecting to Blender
3. Display user's Blender UI link prominently in the interface
