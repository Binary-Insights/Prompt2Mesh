"""
Configuration module for Prompt2Mesh application
Handles dynamic environment detection and URL configuration
"""
import os
from pathlib import Path
from typing import Optional

# Load .env file if it exists (for local development)
try:
    from dotenv import load_dotenv
    # Find .env file in project root
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, rely on system environment variables
    pass


def get_backend_url() -> str:
    """
    Get backend URL based on environment
    
    Priority:
    1. BACKEND_URL environment variable (if set)
    2. Auto-detection based on environment
    
    Auto-detection logic:
    - If running in Docker: http://backend:8000
    - If running locally: http://localhost:8000
    
    Returns:
        Backend URL string
    """
    # Check if explicitly set
    backend_url = os.getenv("BACKEND_URL")
    if backend_url:
        return backend_url
    
    # Auto-detect environment
    if is_running_in_docker():
        return "http://backend:8000"
    else:
        return "http://localhost:8000"


def is_running_in_docker() -> bool:
    """
    Detect if the application is running inside a Docker container
    
    Checks multiple indicators:
    1. /.dockerenv file exists
    2. /proc/1/cgroup contains 'docker'
    3. DOCKER_CONTAINER environment variable
    
    Returns:
        True if running in Docker, False otherwise
    """
    # Check for Docker environment variable
    if os.getenv("DOCKER_CONTAINER"):
        return True
    
    # Check for .dockerenv file
    if os.path.exists("/.dockerenv"):
        return True
    
    # Check cgroup (Linux only)
    try:
        with open("/proc/1/cgroup", "r") as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass
    
    return False


def get_database_url() -> str:
    """
    Get database URL based on environment
    
    Priority:
    1. DATABASE_URL environment variable (if set)
    2. Auto-detection based on environment
    
    Returns:
        Database URL string
    """
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # Auto-detect
    if is_running_in_docker():
        return "postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth"
    else:
        return "postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth"


def get_env_config() -> dict:
    """
    Get complete environment configuration
    
    Returns:
        Dictionary with all configuration values
    """
    return {
        "backend_url": get_backend_url(),
        "database_url": get_database_url(),
        "is_docker": is_running_in_docker(),
        "jwt_secret": os.getenv("JWT_SECRET_KEY", "dev-secret-key"),
        "jwt_expiry_hours": int(os.getenv("JWT_EXPIRY_HOURS", "24")),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    }


def print_config():
    """Print current configuration (for debugging)"""
    config = get_env_config()
    print("=" * 60)
    print("PROMPT2MESH CONFIGURATION")
    print("=" * 60)
    print(f"Environment: {'Docker' if config['is_docker'] else 'Local'}")
    print(f"Backend URL: {config['backend_url']}")
    print(f"Database URL: {config['database_url']}")
    print(f"JWT Expiry: {config['jwt_expiry_hours']} hours")
    print(f"Anthropic API Key: {'✓ Set' if config['anthropic_api_key'] else '✗ Not Set'}")
    print("=" * 60)


if __name__ == "__main__":
    # Test configuration detection
    print_config()
