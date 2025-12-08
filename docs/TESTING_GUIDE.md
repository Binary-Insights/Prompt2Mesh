# Quick Testing Guide - Multi-User Blender Setup

## Current Status
✅ Backend updated with per-user container support
✅ Frontend updated to show Blender UI link
✅ Docker configuration updated
🔄 Backend container rebuilding with `docker` package

## After Build Completes:

### 1. Start Services
```powershell
cd C:\Prompt2Mesh\docker
docker-compose up -d
```

### 2. Verify Backend Started
```powershell
docker logs prompt2mesh-backend
```

Look for:
```
🔐 Initializing authentication service...
✅ Authentication service initialized
🔧 Initializing user session manager...
✅ User session manager initialized
```

### 3. Run Automated Test
```powershell
cd C:\Prompt2Mesh
python test_auto_blender.py
```

Expected output:
```
🔑 Testing login for: testuser2
✅ Login successful
🎨 Blender Instance Created:
   MCP Port: 10000
   Blender UI Port: 13000
   Blender UI URL: http://localhost:13000
```

### 4. Test via Frontend
1. Open: http://localhost:8501
2. Click "Create New Account"
3. Username: `alice`, Password: `alice123`
4. Click "Login"
5. **You should see**: "🎨 Your Blender instance: http://localhost:13000"
6. **Click the link** → Blender UI opens in new tab

### 5. Test Multi-User
```powershell
python test_multi_user.py
```

This creates 2 users and verifies:
- Separate containers created
- Different ports assigned
- No interference between users

## Troubleshooting

### Backend won't start
```powershell
docker logs prompt2mesh-backend
```

Common issues:
- "ModuleNotFoundError: No module named 'docker'" → Rebuild needed (already done)
- "Session manager not available" → Check Docker socket mount in docker-compose.yml

### Container not created
```powershell
docker ps -a | grep blender-
```

If no containers, check:
1. Backend logs for errors
2. Docker daemon running
3. Backend has access to Docker socket

### UI link not showing
Check login response:
```python
import requests
response = requests.post("http://localhost:8000/auth/login", 
                        json={"username": "alice", "password": "alice123"})
print(response.json())
```

Should include:
```json
{
  "blender_ui_url": "http://localhost:13000",
  "mcp_port": 10000,
  "blender_ui_port": 13000
}
```

## What Happens on Login

1. **User submits credentials**
2. **Backend authenticates** → Creates JWT token
3. **Backend calls** `session_manager.create_user_session()`
4. **Docker container created**:
   - Name: `blender-{username}-{user_id}`
   - Image: `prompt2mesh/blender:latest`
   - Ports: MCP (10000+), UI (13000+)
   - Volume: `blender-data-{username}`
5. **Backend returns** Blender UI URL in login response
6. **Frontend displays** clickable link
7. **User clicks** → Blender UI opens

## Container Details

Each user gets:
```bash
Container: blender-alice-4
├── MCP Server: localhost:10000 → container:9876
├── Blender UI: localhost:13000 → container:3000
└── Volume: blender-data-alice (persistent config)
```

## Port Assignments

- User 1: MCP 10000, UI 13000
- User 2: MCP 10001, UI 13001
- User 3: MCP 10002, UI 13002
- etc.

## Verification Commands

```powershell
# View all user containers
docker ps | grep blender-

# View specific user's container
docker logs blender-alice-4

# Check port mappings
docker port blender-alice-4

# View backend logs
docker logs -f prompt2mesh-backend
```

## Success Indicators

✅ Login shows Blender UI link
✅ Container appears in `docker ps`
✅ UI accessible at displayed URL
✅ Multiple users get different ports
✅ Users can work independently
