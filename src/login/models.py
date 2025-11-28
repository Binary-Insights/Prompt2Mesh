"""
Database models for authentication
"""
from sqlalchemy import Column, String, DateTime, Boolean, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    """User model for authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', is_active={self.is_active})>"


class Session(Base):
    """Session model for JWT token storage"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(500), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_valid = Column(Boolean, default=True, nullable=False)
    
    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, is_valid={self.is_valid})>"
