# Multi-User Blender Architecture Guide

## Overview

This architecture provides complete isolation between users. Each user gets their own dedicated Blender container with a unique MCP server port and Blender UI port.

```
┌─────────────────────────────────────────────────────────────┐
│                     Backend Server                           │
│              (Port 8000 - Shared)                            │
│  - Authentication                                            │
│  - User Session Manager                                      │
│  - Creates per-user containers                               │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┬──────────────────┐
        │                     │                   │
        ▼                     ▼                   ▼
┌───────────────┐    ┌───────────────┐   ┌───────────────┐
│ User 1        │    │ User 2        │   │ User 3        │
│ Container     │    │ Container     │   │ Container     │
├───────────────┤    ├───────────────┤   ├───────────────┤
│ Blender       │    │ Blender       │   │ Blender       │
│ MCP: 10000    │    │ MCP: 10001    │   │ MCP: 10002    │
│ UI:  13000    │    │ UI:  13001    │   │ UI:  13002    │
└───────────────┘    └───────────────┘   └───────────────┘
```

## Key Features

✅ **Complete Isolation**: Each user has their own Blender instance
✅ **No Interference**: Users can't affect each other's work
✅ **Dynamic Port Allocation**: Ports assigned automatically (10000+, 13000+)
✅ **Session Lifecycle**: Containers created on login, stopped on logout
✅ **Resource Management**: Idle sessions can be cleaned up
✅ **Persistent Data**: Each user's Blender config saved to named volume

## How It Works

### 1. User Login
```python
POST /auth/login
{
    "username": "shareena",
    "password": "password123"
}
```

**Backend Actions:**
1. Authenticates user
2. Creates/retrieves user session
3. Spawns Docker container with unique ports
4. Returns JWT token

### 2. Container Creation

Each user gets a container named: `blender-{username}-{user_id}`

**Port Mapping:**
- MCP Server: `9876` (internal) → `10000+` (host)
- Blender UI: `3000` (internal) → `13000+` (host)

**Volume Mapping:**
- `blender-data-{username}` → `/home/blender/.config/blender`

### 3. Active Session

User accesses their dedicated:
- Blender UI: `http://localhost:13000`
- MCP connection via port `10000`

Backend connects to user's specific MCP port for all operations.

### 4. User Logout

```python
POST /auth/logout
{
    "token": "eyJ..."
}
```

**Backend Actions:**
1. Invalidates JWT token
2. Stops user's container
3. Releases ports
4. Keeps volume (data persists)

## Configuration

### Environment Variables

```bash
# .env file
ANTHROPIC_API_KEY=your_key_here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prompt2mesh

# Optional
BASE_MCP_PORT=10000        # Starting port for MCP servers
BASE_BLENDER_UI_PORT=13000 # Starting port for Blender UIs
IDLE_TIMEOUT_MINUTES=30    # Auto-cleanup idle sessions
```

### Docker Requirements

```bash
# Ensure Docker is running
docker --version

# Ensure prompt2mesh/blender image exists
docker images | grep prompt2mesh/blender
```

## Deployment

### 1. Build Blender Image

```bash
cd docker
docker build -t prompt2mesh/blender:latest -f dockerfile .
```

### 2. Start Backend

```bash
cd C:\Prompt2Mesh
python src/backend/backend_server.py
```

**Startup Output:**
```
🔐 Initializing authentication service...
✅ Authentication service initialized
🔧 Initializing user session manager...
✅ User session manager initialized
✅ Prompt Refinement Agent initialized
INFO: Uvicorn running on http://0.0.0.0:8000
```

### 3. Start Frontend

```bash
streamlit run src/frontend/login_page.py
```

## Usage Flow

### New User Signup

1. Open http://localhost:8502 (login page)
2. Click "Create New Account"
3. Enter username and password
4. Sign up success → redirect to login

### User Login

1. Enter credentials
2. Backend creates Blender container
3. Wait 5-10 seconds for container startup
4. Access Streamlit interface

### Working with Blender

Each user can:
- Create/modify 3D objects independently
- Use MCP tools (PolyHaven, Sketchfab, Hyper3D)
- Take screenshots
- Execute Blender Python code

**No interference between users!**

### User Logout

1. Click logout
2. Container stops (not deleted)
3. Data preserved in volume
4. Next login: container restarts quickly

## API Endpoints

### Get User Session Info

```bash
GET /user/session?user_id=1
```

**Response:**
```json
{
    "active": true,
    "user_id": 1,
    "username": "shareena",
    "mcp_port": 10000,
    "blender_ui_port": 13000,
    "blender_ui_url": "http://localhost:13000",
    "created_at": "2025-12-06T12:00:00",
    "last_activity": "2025-12-06T12:15:00"
}
```

### List All Active Sessions (Admin)

```bash
GET /admin/sessions
```

### Cleanup Idle Sessions

```bash
POST /admin/cleanup-idle?idle_minutes=30
```

## Resource Management

### Port Allocation

- **MCP Ports**: 10000-10099 (100 concurrent users)
- **Blender UI Ports**: 13000-13099 (100 concurrent users)
- Ports released when container stops

### Container Lifecycle

**Created:** User logs in for the first time
**Reused:** User logs in again (if container exists)
**Stopped:** User logs out or idle timeout
**Removed:** Manual cleanup or server shutdown

### Memory Usage

Per container:
- Base Blender: ~500MB
- With scene data: 1-2GB
- Total for 10 users: ~10-20GB RAM

### Disk Usage

Per user:
- Blender config volume: ~50MB
- Scene data: varies by complexity
- Total for 10 users: ~500MB-1GB

## Monitoring

### Check Active Containers

```bash
docker ps | grep blender-
```

### View Container Logs

```bash
docker logs blender-shareena-1
```

### Monitor Resource Usage

```bash
docker stats
```

## Troubleshooting

### Container Won't Start

**Check Docker logs:**
```bash
docker logs blender-{username}-{user_id}
```

**Common issues:**
- Port already in use
- Docker daemon not running
- Insufficient memory

**Solution:**
```bash
# Restart Docker
# Or change base ports in .env
```

### User Can't Connect to Blender

**Symptoms:**
- MCP connection timeout
- "Could not connect to Blender"

**Checks:**
1. Container is running: `docker ps | grep blender-{username}`
2. Port is accessible: `telnet localhost {mcp_port}`
3. Wait 10 seconds after container creation

### Port Conflicts

**Error:** "Port already allocated"

**Solution:**
```python
# Backend automatically skips used ports
# Or manually change BASE_MCP_PORT in .env
```

### Memory Issues

**Error:** "Cannot create container: insufficient memory"

**Solutions:**
1. Cleanup idle sessions
2. Stop unused containers
3. Increase Docker memory limit

```bash
# Cleanup all stopped containers
docker container prune
```

## Security Considerations

1. **Port Exposure**: Bind to localhost only in production
2. **Container Isolation**: Each user in separate container
3. **Volume Separation**: Per-user volumes prevent cross-contamination
4. **Token Auth**: JWT tokens required for all operations
5. **Resource Limits**: Set CPU/memory limits per container

### Production Hardening

```python
# In user_session_manager.py, add:
container = self.docker_client.containers.run(
    ...
    mem_limit="2g",              # Max 2GB RAM per container
    cpu_quota=50000,             # Max 50% CPU
    network_mode="bridge",       # Isolated network
    security_opt=["no-new-privileges"],
    ...
)
```

## Cost Optimization

### Development (Local)
- Free - uses local resources
- Suitable for 2-3 concurrent users

### Production (Cloud)
- Per user: ~$0.02/hour (t3.medium equivalent)
- 10 concurrent users: ~$0.20/hour
- Idle sessions: $0 (containers stopped)

**Recommendations:**
- Set idle timeout to 15-30 minutes
- Use spot instances for cost savings
- Auto-scale based on active users

## Migration from Single Instance

If you're currently using a single Blender instance:

1. **No code changes needed** in Streamlit
2. Backend automatically manages per-user instances
3. MCP connection happens transparently
4. Users see no difference in UI

**Migration steps:**
1. Deploy new backend with session manager
2. Test with 2 users simultaneously
3. Gradually onboard more users
4. Monitor resource usage

## Next Steps

1. ✅ Deploy and test with 2 users
2. Add admin dashboard for session monitoring
3. Implement auto-scaling based on load
4. Add container health checks
5. Set up logging/metrics collection
6. Configure backup for user volumes
