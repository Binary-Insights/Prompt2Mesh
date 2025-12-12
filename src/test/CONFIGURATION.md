# Configuration Guide

This document explains how to configure Prompt2Mesh for different deployment environments.

## Dynamic URL Configuration

Prompt2Mesh now supports automatic environment detection and dynamic URL configuration. The application automatically selects the correct backend URL based on whether it's running in Docker or locally.

### How It Works

The application uses the `src/config.py` module to automatically detect the environment:

1. **Environment Variable (Highest Priority)**: If `BACKEND_URL` is set, it will be used
2. **Auto-Detection**: Otherwise, the application detects if it's running in Docker:
   - **In Docker**: Uses `http://backend:8000` (Docker service name)
   - **Locally**: Uses `http://localhost:8000` (local development)

### Environment Files

#### `.env` (Root Directory - For Local Development)

```bash
# Backend URL Configuration
# For local development (outside Docker)
BACKEND_URL=http://localhost:8000

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-12345
JWT_EXPIRY_HOURS=24

# PostgreSQL Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth
```

#### `docker/.env` (For Docker Deployment)

```bash
# Backend URL Configuration
# In Docker: use service name
BACKEND_URL=http://backend:8000

# Anthropic API Key
ANTHROPIC_API_KEY=your-api-key-here

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-12345
JWT_EXPIRY_HOURS=24

# PostgreSQL Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=prompt2mesh_auth
```

## Deployment Scenarios

### Local Development (Without Docker)

1. **Set up `.env` file**:
   ```bash
   cp .env.example .env
   # Edit .env and set BACKEND_URL=http://localhost:8000
   ```

2. **Start PostgreSQL locally**:
   ```bash
   sudo service postgresql start
   ```

3. **Initialize database**:
   ```bash
   python init_db.py
   ```

4. **Start backend server**:
   ```bash
   python src/backend/backend_server.py
   ```

5. **Start Streamlit frontend**:
   ```bash
   streamlit run src/frontend/login_page.py
   ```

The application will automatically use `http://localhost:8000` for the backend URL.

### Docker Deployment

1. **Set up Docker environment**:
   ```bash
   cd docker
   cp .env.example .env
   # Edit .env and set your ANTHROPIC_API_KEY
   ```

2. **Build and start containers**:
   ```bash
   docker-compose up -d
   ```

The application will automatically use `http://backend:8000` for inter-container communication.

### Hybrid Setup (Local Frontend + Docker Backend)

If you want to run Streamlit locally but use Docker for the backend:

1. **Start Docker backend only**:
   ```bash
   cd docker
   docker-compose up -d postgres backend
   ```

2. **Set local environment**:
   ```bash
   export BACKEND_URL=http://localhost:8000
   ```

3. **Run Streamlit locally**:
   ```bash
   streamlit run src/frontend/login_page.py
   ```

## Configuration Module API

### `src/config.py`

The configuration module provides several utility functions:

```python
from src.config import get_backend_url, get_database_url, is_running_in_docker

# Get backend URL (auto-detects environment)
backend_url = get_backend_url()

# Check if running in Docker
if is_running_in_docker():
    print("Running in Docker container")

# Get database URL (auto-detects environment)
db_url = get_database_url()

# Get complete configuration
from src.config import get_env_config
config = get_env_config()
print(config)
```

### Testing Configuration

To test your configuration setup:

```bash
# Print current configuration
python src/config.py
```

Output example:
```
============================================================
PROMPT2MESH CONFIGURATION
============================================================
Environment: Local
Backend URL: http://localhost:8000
Database URL: postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth
JWT Expiry: 24 hours
Anthropic API Key: ✓ Set
============================================================
```

## Environment Variables Reference

| Variable | Description | Default (Local) | Default (Docker) |
|----------|-------------|-----------------|------------------|
| `BACKEND_URL` | Backend API URL | `http://localhost:8000` | `http://backend:8000` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth` | `postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth` |
| `JWT_SECRET_KEY` | Secret key for JWT signing | `dev-secret-key` | *Must be set* |
| `JWT_EXPIRY_HOURS` | JWT token expiration time | `24` | `24` |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | *Optional* | *Required* |

## Troubleshooting

### Backend Connection Issues

**Problem**: "Backend server is offline" error

**Solutions**:
1. Check if backend is running:
   ```bash
   curl http://localhost:8000/
   ```

2. Verify environment variable:
   ```bash
   echo $BACKEND_URL  # Linux/Mac
   echo %BACKEND_URL%  # Windows CMD
   $env:BACKEND_URL   # Windows PowerShell
   ```

3. Test configuration:
   ```bash
   python src/config.py
   ```

### Docker Network Issues

**Problem**: Services can't communicate in Docker

**Solutions**:
1. Check Docker network:
   ```bash
   docker network inspect prompt2mesh-network
   ```

2. Verify environment in container:
   ```bash
   docker exec -it prompt2mesh-streamlit env | grep BACKEND_URL
   ```

3. Check container logs:
   ```bash
   docker-compose logs backend
   docker-compose logs streamlit
   ```

### Database Connection Issues

**Problem**: Can't connect to PostgreSQL

**Solutions**:
1. **In Docker**: Use `postgres` as hostname
2. **Locally**: Use `localhost` as hostname
3. Verify PostgreSQL is running:
   ```bash
   # Docker
   docker-compose ps postgres
   
   # Local
   sudo service postgresql status
   ```

## Security Best Practices

1. **Change default credentials**:
   - Update `JWT_SECRET_KEY` in `.env`
   - Change PostgreSQL password in `docker-compose.yml`
   - Update default user credentials (root/root)

2. **Generate strong JWT secret**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Use environment-specific configs**:
   - Never commit `.env` files to version control
   - Use different secrets for development and production
   - Rotate API keys regularly

4. **Enable HTTPS in production**:
   - Use a reverse proxy (nginx/Traefik)
   - Configure SSL certificates
   - Enforce HTTPS redirects

## Migration from Hardcoded URLs

If you have an existing deployment with hardcoded URLs, no changes are needed! The configuration module is backward compatible:

- Old code: `BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")`
- New code: `BACKEND_URL = get_backend_url()`

Both work the same way, but the new approach adds automatic Docker detection.

## Support

For issues or questions about configuration, please check:
- [Docker Setup Guide](docker/README.md)
- [GitHub Issues](https://github.com/Binary-Insights/Prompt2Mesh/issues)
