"""
API Client for Blender Chat Backend
Provides a simple interface for the Streamlit frontend to communicate with the FastAPI backend
"""
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import uuid
import os
import sys
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for imports
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from config import get_backend_url


class BlenderChatAPIClient:
    """Client for communicating with the Blender Chat FastAPI backend"""
    
    def __init__(self, base_url: str = None):
        if base_url is None:
            base_url = get_backend_url()
        self.base_url = base_url.rstrip('/')
        self._session_id = str(uuid.uuid4())  # Generate unique session ID
        
        # Create session with connection pooling and retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=20,
            pool_block=False
        )
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Default timeout for all requests (connect, read)
        self.timeout = (5, 30)  # 5s connect, 30s read
    
    def connect(self, user_id: int = None) -> Dict[str, Any]:
        """Connect to Blender MCP server via backend"""
        params = {"user_id": user_id} if user_id else {}
        response = self.session.post(f"{self.base_url}/connect", params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def disconnect(self) -> Dict[str, Any]:
        """Disconnect from Blender MCP server"""
        response = self.session.post(f"{self.base_url}/disconnect", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def get_status(self) -> Dict[str, Any]:
        """Get connection status"""
        response = self.session.get(f"{self.base_url}/status", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def chat(self, message: str) -> Dict[str, Any]:
        """Send a chat message"""
        response = self.session.post(
            f"{self.base_url}/chat",
            json={"message": message},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def get_history(self) -> Dict[str, Any]:
        """Get conversation history"""
        response = self.session.get(f"{self.base_url}/history", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def clear_history(self) -> Dict[str, Any]:
        """Clear conversation history"""
        response = self.session.post(f"{self.base_url}/clear-history", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
    
    def refine_prompt(self, prompt: str, thread_id: str = "default", detail_level: str = "comprehensive") -> Dict[str, Any]:
        """Refine a user prompt into 3D modeling description with specified detail level"""
        response = self.session.post(
            f"{self.base_url}/refine-prompt",
            json={"prompt": prompt, "thread_id": thread_id, "detail_level": detail_level},
            timeout=self.timeout
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> bool:
        """Check if backend is running"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=(2, 5))
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
