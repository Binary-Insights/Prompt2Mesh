"""
Database connection and session management
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from dotenv import load_dotenv

from .models import Base

# Debug: Print raw environment variable before any processing
import sys
raw_db_url = os.environ.get("DATABASE_URL", "NOT_SET")
print(f"🔍 Raw DATABASE_URL from os.environ: {raw_db_url}", file=sys.stderr, flush=True)

# Only load .env if DATABASE_URL is not already set (Kubernetes sets env vars)
if not os.getenv("DATABASE_URL"):
    print("📁 Loading .env file...", file=sys.stderr, flush=True)
    load_dotenv()
else:
    print("✅ DATABASE_URL already set, skipping .env", file=sys.stderr, flush=True)

# Get database URL from environment or use default
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth"
)

print(f"🔍 Final Database URL: {DATABASE_URL}", file=sys.stderr, flush=True)

# Create engine
engine = create_engine(DATABASE_URL, echo=False)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


@contextmanager
def get_db_session() -> Session:
    """Get database session with automatic cleanup"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
