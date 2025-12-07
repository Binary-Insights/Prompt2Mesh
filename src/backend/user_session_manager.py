"""
User Session Manager
Manages per-user Blender MCP connections and container lifecycle
"""
import docker
import os
import logging
from typing import Dict, Optional
from dataclasses import dataclass
from datetime import datetime
import random

logger = logging.getLogger(__name__)

@dataclass
class UserBlenderSession:
    """Represents a user's Blender session"""
    user_id: int
    username: str
    container_id: str
    container_name: str  # Docker container name for network access
    mcp_port: int
    blender_ui_port: int
    created_at: datetime
    last_activity: datetime
    
class UserSessionManager:
    """Manages per-user Blender instances and MCP connections"""
    
    def __init__(self):
        self.sessions: Dict[int, UserBlenderSession] = {}
        self.docker_client = docker.from_env()
        self.base_mcp_port = 10000  # Start from port 10000
        self.base_blender_ui_port = 13000  # Start from port 13000
        self.allocated_ports = set()
        
    def _allocate_port(self, base_port: int) -> int:
        """Allocate an available port"""
        for i in range(100):  # Try 100 ports
            port = base_port + i
            if port not in self.allocated_ports:
                self.allocated_ports.add(port)
                return port
        raise Exception("No available ports")
    
    def create_user_session(self, user_id: int, username: str) -> UserBlenderSession:
        """Create a new Blender session for a user"""
        
        # Check if session already exists
        if user_id in self.sessions:
            session = self.sessions[user_id]
            # Check if container is still running
            try:
                container = self.docker_client.containers.get(session.container_id)
                if container.status == "running":
                    logger.info(f"User {username} already has an active session")
                    session.last_activity = datetime.utcnow()
                    return session
                else:
                    # Container stopped, remove old session
                    self._cleanup_session(user_id)
            except docker.errors.NotFound:
                # Container doesn't exist, remove old session
                self._cleanup_session(user_id)
        
        # Allocate ports for this user
        mcp_port = self._allocate_port(self.base_mcp_port)
        blender_ui_port = self._allocate_port(self.base_blender_ui_port)
        
        # Container name for Docker network access
        container_name = f"blender-{username}-{user_id}"
        
        # Environment variables for the container
        env_vars = {
            "BLENDER_PORT": str(9876),  # Internal Blender port (same for all)
            "MCP_PORT": str(9876),  # Internal MCP port
            "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY", ""),
            "USER_ID": str(user_id),
            "USERNAME": username
        }
        
        # Create container
        try:
            container = self.docker_client.containers.run(
                image="prompt2mesh/blender-mcp:latest",  # Use custom image with MCP addon
                name=container_name,
                detach=True,
                environment=env_vars,
                ports={
                    '9876/tcp': mcp_port,  # MCP server port
                    '3000/tcp': blender_ui_port  # Blender UI port
                },
                volumes={
                    f"blender-data-{username}": {
                        "bind": "/config",  # linuxserver uses /config
                        "mode": "rw"
                    }
                },
                network="docker_prompt2mesh-network",  # Connect to same network as backend
                restart_policy={"Name": "unless-stopped"}
            )
            
            logger.info(f"Created container {container.id} for user {username}")
            logger.info(f"MCP Port: {mcp_port}, Blender UI Port: {blender_ui_port}")
            
            # Wait for container to be ready
            import time
            time.sleep(5)  # Give container time to start
            
            # Create session object
            session = UserBlenderSession(
                user_id=user_id,
                username=username,
                container_id=container.id,
                container_name=container_name,
                mcp_port=mcp_port,
                blender_ui_port=blender_ui_port,
                created_at=datetime.utcnow(),
                last_activity=datetime.utcnow()
            )
            
            self.sessions[user_id] = session
            return session
            
        except Exception as e:
            logger.error(f"Failed to create container for user {username}: {e}")
            # Release allocated ports
            self.allocated_ports.discard(mcp_port)
            self.allocated_ports.discard(blender_ui_port)
            raise
    
    def get_user_session(self, user_id: int) -> Optional[UserBlenderSession]:
        """Get a user's session if it exists"""
        session = self.sessions.get(user_id)
        if session:
            session.last_activity = datetime.utcnow()
        return session
    
    def stop_user_session(self, user_id: int):
        """Stop a user's Blender session"""
        if user_id not in self.sessions:
            return
        
        session = self.sessions[user_id]
        
        try:
            container = self.docker_client.containers.get(session.container_id)
            container.stop(timeout=10)
            logger.info(f"Stopped container for user {session.username}")
        except docker.errors.NotFound:
            logger.warning(f"Container {session.container_id} not found")
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
        
        self._cleanup_session(user_id)
    
    def _cleanup_session(self, user_id: int):
        """Clean up session data"""
        if user_id in self.sessions:
            session = self.sessions[user_id]
            self.allocated_ports.discard(session.mcp_port)
            self.allocated_ports.discard(session.blender_ui_port)
            del self.sessions[user_id]
    
    def remove_user_session(self, user_id: int):
        """Remove a user's Blender session (stop and delete container)"""
        if user_id not in self.sessions:
            return
        
        session = self.sessions[user_id]
        
        try:
            container = self.docker_client.containers.get(session.container_id)
            container.stop(timeout=10)
            container.remove()
            logger.info(f"Removed container for user {session.username}")
        except docker.errors.NotFound:
            logger.warning(f"Container {session.container_id} not found")
        except Exception as e:
            logger.error(f"Error removing container: {e}")
        
        self._cleanup_session(user_id)
    
    def list_active_sessions(self) -> list[UserBlenderSession]:
        """List all active user sessions"""
        return list(self.sessions.values())
    
    def cleanup_idle_sessions(self, idle_minutes: int = 30):
        """Clean up sessions that have been idle for too long"""
        from datetime import timedelta
        
        now = datetime.utcnow()
        idle_threshold = timedelta(minutes=idle_minutes)
        
        idle_users = []
        for user_id, session in self.sessions.items():
            if now - session.last_activity > idle_threshold:
                idle_users.append(user_id)
        
        for user_id in idle_users:
            logger.info(f"Stopping idle session for user {self.sessions[user_id].username}")
            self.stop_user_session(user_id)
