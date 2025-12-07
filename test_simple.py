"""
Simple test to verify backend endpoints
"""
import requests
import json

BASE_URL = "http://localhost:8000"

def test_backend_health():
    """Test if backend is responding"""
    print("🏥 Testing backend health...")
    try:
        response = requests.get(BASE_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Backend is running!")
            print(f"   Version: {data.get('version')}")
            print(f"   Auth available: {data.get('auth_available')}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_signup(username, password):
    """Test signup endpoint"""
    print(f"\n📝 Testing signup for {username}...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/signup",
            json={"username": username, "password": password},
            timeout=10
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_login(username, password):
    """Test login endpoint"""
    print(f"\n🔑 Testing login for {username}...")
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Login successful!")
            print(f"   User ID: {data.get('user_id')}")
            print(f"   Has token: {bool(data.get('token'))}")
            return data
        else:
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_session_info(user_id):
    """Test session info endpoint"""
    print(f"\n📊 Testing session info for user {user_id}...")
    try:
        response = requests.get(f"{BASE_URL}/user/session?user_id={user_id}", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Active: {data.get('active')}")
            if data.get('active'):
                print(f"   MCP Port: {data.get('mcp_port')}")
                print(f"   UI Port: {data.get('blender_ui_port')}")
                print(f"   UI URL: {data.get('blender_ui_url')}")
            return data
        else:
            print(f"   Response: {response.text[:200]}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    print("=" * 80)
    print("🧪 SIMPLE BACKEND TEST")
    print("=" * 80)
    
    # Test 1: Backend health
    if not test_backend_health():
        print("\n❌ Backend is not responding. Please start it first.")
        return
    
    # Test 2: Signup
    username = "testuser1"
    password = "testpass123"
    test_signup(username, password)
    
    # Test 3: Login
    login_data = test_login(username, password)
    if not login_data:
        print("\n❌ Login failed. Cannot continue.")
        return
    
    # Test 4: Check session
    print("\n⏳ Waiting 5 seconds for container to start...")
    import time
    time.sleep(5)
    
    session_data = test_session_info(login_data['user_id'])
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    if session_data and session_data.get('active'):
        print("✅ All tests passed!")
        print(f"\n🎯 User's Blender container:")
        print(f"   - Username: {username}")
        print(f"   - User ID: {login_data['user_id']}")
        print(f"   - MCP Port: {session_data['mcp_port']}")
        print(f"   - UI Port: {session_data['blender_ui_port']}")
        print(f"   - Access at: {session_data['blender_ui_url']}")
    else:
        print("⚠️  Some tests failed. Check logs above.")

if __name__ == "__main__":
    main()
