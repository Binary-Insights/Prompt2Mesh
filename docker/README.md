# Prompt2Mesh Docker Setup

This directory contains Docker configuration for running Prompt2Mesh with Blender in containers.

## Architecture

The Docker setup includes 4 services:

1. **PostgreSQL** - Database for authentication and sessions
2. **Blender Backend** - Blender container with FastAPI backend
3. **Streamlit Frontend** - Web UI for login and chat
4. **DB Initializer** - One-time setup for database tables and default user

## Quick Start

### 1. Prerequisites

- Docker installed and running
- Docker Compose V2+
- API keys ready

### 2. Configuration

```bash
# Copy environment template
cd docker
cp .env.example .env

# Edit .env and add your API key
nano .env
# Set ANTHROPIC_API_KEY=your-actual-api-key
```

### 3. Build and Run

```bash
# Build images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

### 4. Access Services

- **Blender Web UI**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Streamlit UI**: http://localhost:8501

### 5. Login

Navigate to http://localhost:8501 and login with:
- **Username**: `root`
- **Password**: `root`

## Services Overview

### PostgreSQL (`postgres`)
- **Port**: 5432
- **Database**: prompt2mesh_auth
- **User**: postgres / postgres
- **Volume**: `postgres_data` for persistence

### Blender Backend (`blender-backend`)
- **Ports**: 
  - 3000 - Blender Web UI (KasmVNC)
  - 3001 - Blender VNC (optional)
  - 8000 - FastAPI Backend
- **Base Image**: linuxserver/blender:latest
- **Volumes**:
  - `blender_config` - Blender settings
  - `./blender_projects` - Project files
  - Application source mounted from host

### Streamlit Frontend (`streamlit`)
- **Port**: 8501
- **Purpose**: Web UI for authentication and chat
- **Depends on**: Backend API

### DB Initializer (`db-init`)
- **Purpose**: Creates database tables and default user
- **Runs**: Once on first startup
- **Restart**: Never (one-time setup)

## Docker Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### Restart Specific Service
```bash
docker-compose restart blender-backend
docker-compose restart streamlit
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f blender-backend
docker-compose logs -f streamlit
docker-compose logs -f postgres
```

### Rebuild Images
```bash
# Rebuild all
docker-compose build --no-cache

# Rebuild specific service
docker-compose build --no-cache blender-backend
```

### Access Container Shell
```bash
# Backend container
docker-compose exec blender-backend /bin/bash

# Database container
docker-compose exec postgres psql -U postgres -d prompt2mesh_auth
```

### Check Service Health
```bash
docker-compose ps
```

## Volumes

### Persistent Data
- `postgres_data` - Database data (persists across restarts)
- `blender_config` - Blender configuration

### Mounted Directories
- `./blender_projects` - Store your Blender project files here
- `../src` - Application source code (live reload during development)
- `../requirements` - Modeling requirement files
- `../screenshots` - Generated screenshots

## Environment Variables

### Required
- `ANTHROPIC_API_KEY` - Your Anthropic API key

### Optional
- `JWT_SECRET_KEY` - JWT signing key (auto-generated if not set)
- `JWT_EXPIRY_HOURS` - Token expiration time (default: 24)
- `TZ` - Timezone (default: America/New_York)
- `PUID/PGID` - User/Group IDs for file permissions (default: 1000)

## Networking

All services communicate via the `prompt2mesh-network` bridge network:

```
Internet
    │
    ├─→ localhost:8501 → Streamlit Frontend
    ├─→ localhost:8000 → Backend API
    ├─→ localhost:3000 → Blender Web UI
    └─→ localhost:5432 → PostgreSQL
         ↑
         │ (Internal network)
         │
    [Streamlit] ←→ [Backend] ←→ [Postgres]
                      ↓
                  [Blender]
```

## Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# Check logs
docker-compose logs

# Restart all services
docker-compose down
docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose exec postgres pg_isready

# Verify database exists
docker-compose exec postgres psql -U postgres -l

# Reinitialize database
docker-compose restart db-init
```

### Backend API Not Responding

```bash
# Check backend logs
docker-compose logs blender-backend

# Restart backend
docker-compose restart blender-backend

# Check health
curl http://localhost:8000/
```

### Blender UI Not Loading

```bash
# Check Blender container logs
docker-compose logs blender-backend | grep -i blender

# Access via browser
# http://localhost:3000
```

### Permission Errors

```bash
# Fix file permissions
sudo chown -R $USER:$USER ../src ../requirements ../screenshots

# Or adjust PUID/PGID in .env to match your user
id -u  # Get your PUID
id -g  # Get your PGID
```

## Development Mode

For development with live code reload:

```bash
# Edit docker-compose.yml to mount src directory
# (already configured by default)

# Restart services to pick up changes
docker-compose restart blender-backend streamlit
```

## Production Deployment

### Security Checklist

1. **Change default credentials**:
   ```bash
   # Generate strong JWT secret
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Update database password**:
   ```yaml
   # In docker-compose.yml
   POSTGRES_PASSWORD: use-strong-password-here
   ```

3. **Enable HTTPS**:
   - Add reverse proxy (nginx, Traefik)
   - Configure SSL certificates

4. **Restrict network access**:
   ```yaml
   # Remove port mappings for internal services
   # Only expose necessary ports
   ```

5. **Enable resource limits**:
   ```yaml
   services:
     blender-backend:
       deploy:
         resources:
           limits:
             cpus: '2'
             memory: 4G
   ```

## Backup and Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U postgres prompt2mesh_auth > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker-compose exec -T postgres psql -U postgres prompt2mesh_auth
```

### Backup Volumes
```bash
docker run --rm -v postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres_backup.tar.gz /data
```

## Updating

```bash
# Pull latest images
docker-compose pull

# Rebuild and restart
docker-compose up -d --build

# Clean up old images
docker image prune -a
```

## Cleanup

### Remove All Containers and Volumes
```bash
# Stop and remove containers
docker-compose down

# Remove volumes (WARNING: deletes data)
docker-compose down -v

# Remove images
docker-compose down --rmi all
```

### Remove Only Containers
```bash
docker-compose down
```

## Support

For issues and questions:
- Check logs: `docker-compose logs -f`
- Verify health: `docker-compose ps`
- Review configuration: `docker-compose config`
