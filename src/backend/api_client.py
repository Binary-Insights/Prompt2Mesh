"""
API Client for Blender Chat Backend
Provides a simple interface for the Streamlit frontend to communicate with the FastAPI backend
"""
import requests
import uuid
from typing import Dict, Any, List


class BlenderChatAPIClient:
    """Client for communicating with the Blender Chat FastAPI backend"""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self._session_id = str(uuid.uuid4())  # Generate unique session ID
    
    def connect(self) -> Dict[str, Any]:
        """Connect to Blender MCP server via backend"""
        response = requests.post(f"{self.base_url}/connect")
        response.raise_for_status()
        return response.json()
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from Blender MCP server"""
        response = requests.post(f"{self.base_url}/disconnect")
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        response = requests.get(f"{self.base_url}/status")
        response.raise_for_status()
        return response.json()
    
    def chat(self, message: str) -> Dict[str, Any]:
        """Send a chat message"""
        response = requests.post(
            f"{self.base_url}/chat",
            json={"message": message}
        )
        response.raise_for_status()
        return response.json()
    
    def get_history(self) -> Dict[str, Any]:
        """Get conversation history"""
        response = requests.get(f"{self.base_url}/history")
        response.raise_for_status()
        return response.json()
    
    def clear_history(self) -> Dict[str, Any]:
        """Clear conversation history"""
        response = requests.post(f"{self.base_url}/clear-history")
        response.raise_for_status()
        return response.json()
    
    def refine_prompt(self, prompt: str, thread_id: str = "default") -> Dict[str, Any]:
        """Refine a user prompt into comprehensive 3D modeling description"""
        response = requests.post(
            f"{self.base_url}/refine-prompt",
            json={"prompt": prompt, "thread_id": thread_id}
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        """Check if backend is running"""
        try:
            response = requests.get(f"{self.base_url}/")
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
