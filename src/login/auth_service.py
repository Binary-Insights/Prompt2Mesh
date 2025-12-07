"""
Authentication service for JWT token management
"""
import os
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv

from .database import get_db_session
from .models import User, Session

load_dotenv()


class AuthService:
    """Service for handling authentication operations"""
    
    def __init__(self):
        self.secret_key = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
        self.algorithm = "HS256"
        self.token_expiry_hours = int(os.getenv("JWT_EXPIRY_HOURS", "24"))
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    
    def create_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Create a new user and return user info"""
        with get_db_session() as session:
            # Check if user exists
            existing_user = session.query(User).filter(User.username == username).first()
            if existing_user:
                return None
            
            # Create new user
            password_hash = self.hash_password(password)
            new_user = User(username=username, password_hash=password_hash)
            session.add(new_user)
            session.commit()
            session.refresh(new_user)
            
            # Return user data before session closes
            return {
                "id": new_user.id,
                "username": new_user.username
            }
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """
        Authenticate a user and return JWT token
        
        Returns:
            Dict with token and user info if successful, None otherwise
        """
        with get_db_session() as session:
            # Find user
            user = session.query(User).filter(User.username == username).first()
            
            if not user or not user.is_active:
                return None
            
            # Verify password
            if not self.verify_password(password, user.password_hash):
                return None
            
            # Generate JWT token
            token = self._generate_token(user.id, user.username)
            
            # Store session in database
            expires_at = datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
            new_session = Session(
                user_id=user.id,
                token=token,
                expires_at=expires_at
            )
            session.add(new_session)
            session.commit()
            
            return {
                "token": token,
                "user_id": user.id,
                "username": user.username,
                "expires_at": expires_at.isoformat()
            }
    
    def _generate_token(self, user_id: int, username: str) -> str:
        """Generate JWT token"""
        payload = {
            "user_id": user_id,
            "username": username,
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify JWT token and check if it's valid in database
        
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            # Decode JWT
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if session exists and is valid in database
            with get_db_session() as session:
                db_session = session.query(Session).filter(
                    Session.token == token,
                    Session.is_valid == True,
                    Session.expires_at > datetime.utcnow()
                ).first()
                
                if not db_session:
                    return None
                
                return payload
        
        except jwt.ExpiredSignatureError:
            # Token expired - invalidate in database
            self._invalidate_token(token)
            return None
        except jwt.InvalidTokenError:
            return None
    
    def _invalidate_token(self, token: str):
        """Mark a token as invalid in database"""
        with get_db_session() as session:
            db_session = session.query(Session).filter(Session.token == token).first()
            if db_session:
                db_session.is_valid = False
                session.commit()
    
    def logout(self, token: str) -> bool:
        """Logout user by invalidating token"""
        self._invalidate_token(token)
        return True
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from database"""
        with get_db_session() as session:
            expired_sessions = session.query(Session).filter(
                Session.expires_at < datetime.utcnow()
            ).all()
            
            count = len(expired_sessions)
            for sess in expired_sessions:
                session.delete(sess)
            
            session.commit()
            
            return count
