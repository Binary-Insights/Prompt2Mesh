"""
Test login with timeout fix
"""
import requests
import time

BASE_URL = "http://localhost:8000"

def test_new_user_login():
    """Test creating a new user and logging in"""
    
    # Create unique username
    username = f"testuser_{int(time.time())}"
    password = "testpass123"
    
    print("=" * 80)
    print("🧪 TESTING LOGIN TIMEOUT FIX")
    print("=" * 80)
    
    # Step 1: Create user
    print(f"\n1️⃣ Creating user: {username}")
    response = requests.post(
        f"{BASE_URL}/auth/signup",
        json={"username": username, "password": password},
        timeout=10
    )
    
    if response.status_code == 200:
        print(f"   ✅ User created")
    else:
        print(f"   ❌ Failed: {response.text}")
        return
    
    # Step 2: Login (this will create container)
    print(f"\n2️⃣ Logging in (will create Docker container)...")
    print(f"   ⏳ This may take 10-15 seconds...")
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=30  # 30 second timeout
        )
        
        elapsed = time.time() - start_time
        print(f"\n   ⏱️  Response received in {elapsed:.1f} seconds")
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n   ✅ Login successful!")
            print(f"   Username: {data.get('username')}")
            print(f"   User ID: {data.get('user_id')}")
            
            if data.get('blender_ui_url'):
                print(f"\n   🎨 Blender Instance Ready:")
                print(f"      MCP Port: {data.get('mcp_port')}")
                print(f"      UI Port: {data.get('blender_ui_port')}")
                print(f"      URL: {data.get('blender_ui_url')}")
            else:
                print(f"\n   ⏳ Blender container is being created...")
                print(f"      It will be available shortly")
            
            return data
        else:
            print(f"   ❌ Login failed: {response.text}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"\n   ❌ Login timed out after 30 seconds!")
        print(f"   This suggests the container creation is taking too long")
        return None
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        return None

def main():
    login_data = test_new_user_login()
    
    if login_data:
        print("\n" + "=" * 80)
        print("✅ TEST PASSED")
        print("=" * 80)
        print("\n📝 Summary:")
        print("   • Login completed without timeout")
        print("   • Container creation handled properly")
        print("   • User can proceed to application")
        
        if login_data.get('blender_ui_url'):
            print(f"\n🚀 Ready to use: {login_data['blender_ui_url']}")
        else:
            print(f"\n⏳ Container will be ready in a few seconds")
            print(f"   User ID: {login_data['user_id']}")
            print(f"\n   Check status with:")
            print(f"   curl http://localhost:8000/user/session?user_id={login_data['user_id']}")
    else:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED")
        print("=" * 80)

if __name__ == "__main__":
    main()
