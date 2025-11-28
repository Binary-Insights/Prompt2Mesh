# Quick Start Guide - JWT Authentication

## Prerequisites

1. PostgreSQL installed and running
2. Python 3.11+ with dependencies installed
3. Environment variables configured

## Step-by-Step Setup

### 1. Install PostgreSQL

**Windows (PowerShell):**
```powershell
# Download installer from https://www.postgresql.org/download/windows/
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
# Access PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE prompt2mesh_auth;

# Exit
\q
```

### 3. Install Python Dependencies

```bash
# Install all dependencies
pip install sqlalchemy psycopg2-binary pyjwt bcrypt requests

# Or install entire project
pip install -e .
```

### 4. Configure Environment

Create `.env` file in project root:

```bash
# Copy example
cp .env.example .env

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit .env and add your secret key
JWT_SECRET_KEY=<paste-generated-key-here>
JWT_EXPIRY_HOURS=24
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth
```

### 5. Initialize Database

```bash
python init_db.py
```

Expected output:
```
============================================================
Prompt2Mesh - Database Initialization
============================================================

📊 Database URL: postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth

🔧 Creating database tables...
✅ Database tables created successfully

👤 Creating default user...
✅ Default 'root' user created successfully
   Username: root
   Password: root
   ⚠️  Please change this password in production!

============================================================
✅ Database initialization complete!
============================================================
```

### 6. Start Backend Server

```bash
python src/backend/backend_server.py
```

Expected output:
```
🔐 Initializing authentication service...
✅ Database tables created successfully
✅ Authentication service initialized
✅ Prompt Refinement Agent initialized

INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 7. Start Streamlit Frontend

**New terminal:**
```bash
streamlit run src/frontend/login_page.py
```

Browser will open automatically at `http://localhost:8501`

### 8. Login

1. Enter credentials:
   - **Username:** `root`
   - **Password:** `root`

2. Click "Login"

3. You'll be redirected to the Artisan Agent page

## Verify Installation

### Test Database Connection

```bash
psql -U postgres -d prompt2mesh_auth

# Check tables
\dt

# Check root user exists
SELECT * FROM users;

# Exit
\q
```

### Test API Endpoints

```bash
# Check backend is running
curl http://localhost:8000/

# Test login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"root","password":"root"}'
```

## Troubleshooting

### PostgreSQL Not Running

**Windows:**
```powershell
# Check service status
Get-Service -Name postgresql*

# Start service
Start-Service postgresql-x64-14  # Adjust version number
```

**Linux/WSL:**
```bash
sudo systemctl status postgresql
sudo systemctl start postgresql
```

### Database Connection Failed

1. Verify PostgreSQL is running
2. Check credentials in `.env`
3. Ensure database exists: `psql -U postgres -l`

### Port Already in Use

**Backend (Port 8000):**
```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux

# Kill process
taskkill /PID <pid> /F        # Windows
kill -9 <pid>                 # Linux
```

**Streamlit (Port 8501):**
```bash
# Find and kill
netstat -ano | findstr :8501  # Windows
lsof -i :8501                 # Linux
```

### Import Errors

```bash
# Ensure you're in project root
cd /path/to/Prompt2Mesh

# Reinstall dependencies
pip install -e .
```

## Next Steps

1. **Change Default Password:**
   - Login as root
   - Create new admin user via Python script
   - Disable root account or change password

2. **Create Additional Users:**
   ```python
   from src.login import AuthService
   
   auth = AuthService()
   auth.create_user("yourname", "securepassword")
   ```

3. **Secure for Production:**
   - Use strong `JWT_SECRET_KEY`
   - Enable HTTPS
   - Change database credentials
   - Set up firewall rules

## Architecture Overview

```
User Browser
    │
    ├─── http://localhost:8501 (Streamlit - Login Page)
    │         │
    │         └─── After Auth ──▶ Artisan Agent Page
    │
    └─── http://localhost:8000 (FastAPI Backend)
              │
              ├─── /auth/login
              ├─── /auth/verify  
              ├─── /auth/logout
              └─── /artisan/*
                      │
                      └─── PostgreSQL Database
                              ├─── users table
                              └─── sessions table
```

## File Locations

```
Prompt2Mesh/
├── .env                        # Your configuration (create this)
├── .env.example                # Template configuration
├── init_db.py                  # Database initialization script
├── AUTH_SETUP.md              # Detailed documentation
├── QUICKSTART_AUTH.md         # This file
│
├── src/
│   ├── login/                  # Authentication package
│   │   ├── __init__.py
│   │   ├── models.py           # User & Session models
│   │   ├── database.py         # Database connection
│   │   └── auth_service.py     # JWT logic
│   │
│   ├── backend/
│   │   └── backend_server.py   # FastAPI with auth endpoints
│   │
│   └── frontend/
│       ├── login_page.py       # LOGIN HERE (entry point)
│       └── pages/
│           └── artisan_page.py # Protected page
```

## Default Credentials

```
Username: root
Password: root
```

**⚠️ IMPORTANT:** Change these credentials before deploying to production!

## Support

For detailed information, see `AUTH_SETUP.md`
