"""
Database Initialization Script
Creates database tables and inserts default root user
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.login import init_db, AuthService, get_db_session
from src.login.models import User


def create_default_user():
    """Create default root user if not exists"""
    auth_service = AuthService()
    
    with get_db_session() as session:
        # Check if root user exists
        existing_user = session.query(User).filter(User.username == "root").first()
        
        if existing_user:
            print("✅ Default 'root' user already exists")
            return
        
        # Create root user
        password_hash = auth_service.hash_password("root")
        root_user = User(
            username="root",
            password_hash=password_hash,
            is_active=True
        )
        
        session.add(root_user)
        session.commit()
        
        print("✅ Default 'root' user created successfully")
        print("   Username: root")
        print("   Password: root")
        print("   ⚠️  Please change this password in production!")


def main():
    """Main initialization function"""
    print("=" * 60)
    print("Prompt2Mesh - Database Initialization")
    print("=" * 60)
    print()
    
    # Check database URL
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/prompt2mesh_auth")
    print(f"📊 Database URL: {db_url}")
    print()
    
    # Initialize database tables
    print("🔧 Creating database tables...")
    try:
        init_db()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return
    
    print()
    
    # Create default user
    print("👤 Creating default user...")
    try:
        create_default_user()
    except Exception as e:
        print(f"❌ Error creating default user: {e}")
        return
    
    print()
    print("=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Start the backend server: python src/backend/backend_server.py")
    print("2. Start Streamlit: streamlit run src/frontend/login_page.py")
    print("3. Login with username 'root' and password 'root'")
    print()


if __name__ == "__main__":
    main()
