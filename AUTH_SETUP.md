# JWT Authentication System

This document describes the JWT authentication system implemented for Prompt2Mesh.

## Overview

The authentication system provides secure login functionality with JWT tokens stored in PostgreSQL database.

## Architecture

### Components

1. **Database Layer** (`src/login/`)
   - `models.py`: SQLAlchemy models for User and Session tables
   - `database.py`: Database connection and session management
   - `auth_service.py`: Authentication service with JWT token management

2. **Backend API** (`src/backend/backend_server.py`)
   - `/auth/login`: Authenticate user and return JWT token
   - `/auth/verify`: Verify token validity
   - `/auth/logout`: Invalidate token

3. **Frontend** (`src/frontend/`)
   - `login_page.py`: Login interface (entry point)
   - `pages/artisan_page.py`: Protected Artisan Agent interface

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

### Sessions Table
```sql
CREATE TABLE sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    token VARCHAR(500) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP NOT NULL,
    is_valid BOOLEAN DEFAULT TRUE
);
```

## Setup Instructions

### 1. Install PostgreSQL

**Windows:**
```powershell
# Download from https://www.postgresql.org/download/windows/
# Or use Chocolatey
choco install postgresql
```

**Linux/WSL:**
```bash
sudo apt update
sudo apt install postgresql postgresql-contrib
sudo systemctl start postgresql
```

### 2. Create Database

```bash
# Login to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE prompt2mesh_auth;

# Exit
\q
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and update:

```bash
# Generate a strong secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file
JWT_SECRET_KEY=<generated-secret-key>
JWT_EXPIRY_HOURS=24
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
# Or
uv pip install -e .
```

### 5. Initialize Database

```bash
python init_db.py
```

This will:
- Create database tables (users, sessions)
- Create default root user (username: `root`, password: `root`)

### 6. Start Backend Server

```bash
python src/backend/backend_server.py
```

Server will start on `http://localhost:8000`

### 7. Start Streamlit Frontend

```bash
streamlit run src/frontend/login_page.py
```

## Usage

### Login Flow

1. Navigate to login page (automatically opens)
2. Enter credentials:
   - Username: `root`
   - Password: `root`
3. Click "Login"
4. Upon successful authentication:
   - JWT token stored in session state
   - Redirected to Artisan Agent page

### Session Management

- Tokens expire after 24 hours (configurable via `JWT_EXPIRY_HOURS`)
- Token validity checked on each page load
- Expired sessions automatically redirect to login page
- Logout invalidates token in database

### Protected Routes

All pages in `src/frontend/pages/` are protected and require authentication:
- `artisan_page.py`: Artisan Agent modeling interface

## API Reference

### POST /auth/login

Authenticate user and receive JWT token.

**Request:**
```json
{
  "username": "root",
  "password": "root"
}
```

**Response:**
```json
{
  "success": true,
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user_id": 1,
  "username": "root",
  "expires_at": "2025-11-29T12:00:00"
}
```

### POST /auth/verify

Verify if token is still valid.

**Request:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "valid": true,
  "user_id": 1,
  "username": "root",
  "message": "Token is valid"
}
```

### POST /auth/logout

Invalidate token and logout.

**Request:**
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Security Considerations

### Production Deployment

1. **Change Default Credentials:**
   ```python
   # Use init_db.py to create custom users
   # Or directly insert into database
   ```

2. **Use Strong Secret Key:**
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

3. **Enable HTTPS:**
   - Use reverse proxy (nginx, Apache)
   - Enable SSL certificates
   - Update CORS settings in backend_server.py

4. **Database Security:**
   - Use strong database passwords
   - Enable SSL for database connections
   - Restrict database access to localhost or VPN

5. **Token Expiry:**
   - Adjust `JWT_EXPIRY_HOURS` based on security needs
   - Implement refresh tokens for long sessions

6. **Rate Limiting:**
   - Add rate limiting to login endpoint
   - Implement account lockout after failed attempts

### Password Management

Passwords are hashed using bcrypt with automatic salt generation:

```python
# Hashing (during registration/password change)
salt = bcrypt.gensalt()
password_hash = bcrypt.hashpw(password.encode('utf-8'), salt)

# Verification (during login)
bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
```

## Adding New Users

### Via Python Script

```python
from src.login import AuthService

auth = AuthService()
auth.create_user("newuser", "securepassword")
```

### Via Database

```sql
-- Hash password using Python first
-- python -c "import bcrypt; print(bcrypt.hashpw(b'password', bcrypt.gensalt()).decode())"

INSERT INTO users (username, password_hash, is_active)
VALUES ('newuser', '$2b$12$...hashed_password...', TRUE);
```

## Troubleshooting

### Database Connection Errors

```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Verify database exists
psql -U postgres -l

# Test connection
psql -U postgres -d prompt2mesh_auth
```

### Token Verification Failures

- Check `JWT_SECRET_KEY` matches in .env
- Verify token hasn't expired
- Check database session is valid

### Frontend Redirect Issues

- Clear browser cache
- Check `st.session_state` in Streamlit
- Verify backend is running on correct port

## Maintenance

### Cleanup Expired Sessions

```python
from src.login import AuthService

auth = AuthService()
count = auth.cleanup_expired_sessions()
print(f"Cleaned up {count} expired sessions")
```

### Backup Database

```bash
pg_dump -U postgres prompt2mesh_auth > backup.sql
```

### Restore Database

```bash
psql -U postgres prompt2mesh_auth < backup.sql
```

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit Frontend                        │
│  ┌──────────────┐              ┌────────────────────────┐  │
│  │  login_page  │──────────────▶│  pages/artisan_page   │  │
│  │   (Entry)    │  Auth Check   │     (Protected)       │  │
│  └──────────────┘              └────────────────────────┘  │
└────────────┬────────────────────────────────┬───────────────┘
             │                                │
             │ HTTP Requests (JWT Token)      │
             │                                │
┌────────────▼────────────────────────────────▼───────────────┐
│                   Backend API (FastAPI)                      │
│  ┌──────────────────┐         ┌──────────────────────────┐ │
│  │  Auth Endpoints  │         │   Artisan Endpoints      │ │
│  │  /auth/login     │         │   /artisan/model         │ │
│  │  /auth/verify    │         │   /artisan/status        │ │
│  │  /auth/logout    │         │   /artisan/tasks         │ │
│  └────────┬─────────┘         └──────────────────────────┘ │
└───────────┼──────────────────────────────────────────────────┘
            │
            │ Database Queries
            │
┌───────────▼──────────────────────────────────────────────────┐
│                   PostgreSQL Database                         │
│  ┌──────────────────┐         ┌──────────────────────────┐  │
│  │   users table    │         │   sessions table         │  │
│  │  - id            │         │   - id                   │  │
│  │  - username      │         │   - user_id              │  │
│  │  - password_hash │         │   - token                │  │
│  │  - created_at    │         │   - expires_at           │  │
│  │  - is_active     │         │   - is_valid             │  │
│  └──────────────────┘         └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## File Structure

```
Prompt2Mesh/
├── src/
│   ├── login/
│   │   ├── __init__.py
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── database.py         # DB connection
│   │   └── auth_service.py     # JWT authentication
│   │
│   ├── backend/
│   │   └── backend_server.py   # FastAPI + auth endpoints
│   │
│   └── frontend/
│       ├── login_page.py       # Login UI (entry point)
│       └── pages/
│           └── artisan_page.py # Protected Artisan UI
│
├── init_db.py                  # Database initialization
├── .env                        # Environment variables
├── .env.example                # Example configuration
└── AUTH_SETUP.md              # This file
```
