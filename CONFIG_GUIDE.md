# Configuration Guide

## Dynamic Environment Detection

The application now automatically detects whether it's running in Docker or locally and configures the backend URL accordingly.

## Configuration Module: `src/config.py`

The `config.py` module provides centralized configuration management with automatic environment detection:

```python
from src.config import get_backend_url

# Automatically returns:
# - http://backend:8000 (when running in Docker)
# - http://localhost:8000 (when running locally)
backend_url = get_backend_url()
```

### How It Works

1. **Environment Detection**: Checks for Docker environment indicators:
   - `/.dockerenv` file exists
   - `KUBERNETES_SERVICE_HOST` environment variable
   - `container=docker` in `/proc/1/cgroup`

2. **URL Selection**:
   - **Docker**: Uses `http://backend:8000` (Docker service name)
   - **Local**: Uses `http://localhost:8000`
   - **Custom**: Can override with `BACKEND_URL` environment variable

3. **Environment Variables**: Loaded from `.env` file using `python-dotenv`

## Environment Variables

### Root `.env` File (for local development)

```bash
# Backend URL (optional - auto-detected if not set)
BACKEND_URL=http://localhost:8000

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production-12345
JWT_EXPIRY_HOURS=24

# PostgreSQL Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth

# Anthropic API Key
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Docker `.env` File (for Docker deployment)

Create `docker/.env` from `docker/.env.example`:

```bash
cd docker
cp .env.example .env
# Edit .env with your actual API keys
```

Required variables for Docker:
```bash
# Auto-uses service name in Docker
BACKEND_URL=http://backend:8000

# Required API key
ANTHROPIC_API_KEY=your-actual-api-key

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-key
JWT_EXPIRY_HOURS=24
```

## Usage in Application Files

All frontend files now use the centralized configuration:

### `login_page.py`
```python
from src.config import get_backend_url
BACKEND_URL = get_backend_url()
```

### `artisan_page.py`
```python
from config import get_backend_url
BACKEND_URL = get_backend_url()
```

### `api_client.py`
```python
from src.config import get_backend_url
client = BlenderChatAPIClient(get_backend_url())
```

## Testing Configuration

Test the configuration by running:

```bash
# Activate virtual environment
source .venv/bin/activate  # Linux/Mac
.venv_win\Scripts\Activate.ps1  # Windows

# Run config test
python src/config.py
```

Expected output:
```
============================================================
PROMPT2MESH CONFIGURATION
============================================================
Environment: Local (or Docker)
Backend URL: http://localhost:8000 (or http://backend:8000)
Database URL: postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth
JWT Expiry: 24 hours
Anthropic API Key: ✓ Set
============================================================
```

## Docker Deployment

The docker-compose configuration automatically sets environment variables:

```yaml
streamlit:
  environment:
    BACKEND_URL: ${BACKEND_URL:-http://backend:8000}
    ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    DATABASE_URL: postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth
```

**Note**: The `BACKEND_URL` defaults to `http://backend:8000` in Docker, but can be overridden in `docker/.env` if needed.

## Security Best Practices

1. **Never commit `.env` files** - They contain sensitive credentials
2. **Generate strong JWT secrets**:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **Change default passwords** in production
4. **Use environment-specific `.env` files**:
   - `.env` for local development
   - `docker/.env` for Docker deployment
   - Never share these files

## Troubleshooting

### Backend connection fails in Docker
- Check `docker-compose logs streamlit` and `docker-compose logs backend`
- Verify `BACKEND_URL=http://backend:8000` in docker/.env
- Ensure containers are on same network: `docker network inspect prompt2mesh-network`

### Backend connection fails locally
- Check backend is running: `curl http://localhost:8000/`
- Verify `.env` has correct `BACKEND_URL=http://localhost:8000`
- Ensure PostgreSQL is running locally

### Configuration not loading
- Verify `python-dotenv` is installed: `pip install python-dotenv`
- Check `.env` file exists in project root
- Run `python src/config.py` to test configuration

## Architecture

```
Local Development:
┌─────────────┐     http://localhost:8000     ┌─────────────┐
│  Streamlit  │ ────────────────────────────> │   FastAPI   │
│   Frontend  │                                │   Backend   │
└─────────────┘                                └─────────────┘

Docker Deployment:
┌─────────────┐     http://backend:8000       ┌─────────────┐
│  Streamlit  │ ────────────────────────────> │   FastAPI   │
│  Container  │    (Docker network)            │  Container  │
└─────────────┘                                └─────────────┘
```

The application automatically chooses the correct URL based on the runtime environment.
