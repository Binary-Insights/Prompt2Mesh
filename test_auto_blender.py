"""
Test automatic Blender instance creation and UI opening on login
"""
import requests
import time
import webbrowser

BASE_URL = "http://localhost:8000"

def test_login_with_blender_ui(username, password):
    """Test login and check if Blender UI URL is returned"""
    print(f"\n🔑 Testing login for: {username}")
    print(f"   Logging in...")
    
    response = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": username, "password": password},
        timeout=30
    )
    
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n✅ Login successful!")
        print(f"   Username: {data.get('username')}")
        print(f"   User ID: {data.get('user_id')}")
        print(f"   Token: {data.get('token', '')[:20]}...")
        
        # Check for Blender session info
        if data.get('blender_ui_url'):
            print(f"\n🎨 Blender Instance Created:")
            print(f"   MCP Port: {data.get('mcp_port')}")
            print(f"   Blender UI Port: {data.get('blender_ui_port')}")
            print(f"   Blender UI URL: {data.get('blender_ui_url')}")
            print(f"\n🚀 Opening Blender UI in browser...")
            return data
        else:
            print(f"\n⚠️  No Blender session info returned")
            print(f"   This means session_manager might not be initialized")
            return data
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def check_container_running(username, user_id):
    """Check if user's container is running"""
    import subprocess
    print(f"\n🐳 Checking if container is running...")
    container_name = f"blender-{username}-{user_id}"
    
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True
        )
        
        if container_name in result.stdout:
            print(f"   ✅ Container {container_name} is running!")
            return True
        else:
            print(f"   ❌ Container {container_name} not found")
            print(f"   All Blender containers:")
            subprocess.run(["docker", "ps", "--filter", "name=blender-"])
            return False
    except Exception as e:
        print(f"   ❌ Error checking container: {e}")
        return False

def test_blender_ui_accessible(url, timeout=10):
    """Test if Blender UI is accessible"""
    print(f"\n🌐 Testing Blender UI accessibility...")
    print(f"   URL: {url}")
    
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                print(f"   ✅ Blender UI is accessible!")
                return True
        except:
            time.sleep(1)
    
    print(f"   ⚠️  Blender UI not accessible yet (container may still be starting)")
    return False

def main():
    print("=" * 80)
    print("🧪 AUTOMATIC BLENDER INSTANCE TEST")
    print("=" * 80)
    
    # Test credentials
    username = "testuser2"
    password = "testpass123"
    
    print(f"\n📝 Test user: {username}")
    
    # First, try to create the user (ignore if exists)
    print(f"\n🔐 Creating user (if doesn't exist)...")
    try:
        requests.post(
            f"{BASE_URL}/auth/signup",
            json={"username": username, "password": password},
            timeout=10
        )
        print(f"   User created or already exists")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n" + "=" * 80)
    print("PHASE 1: LOGIN & CONTAINER CREATION")
    print("=" * 80)
    
    # Login and get Blender UI info
    login_data = test_login_with_blender_ui(username, password)
    
    if not login_data:
        print("\n❌ Login failed. Cannot continue.")
        return
    
    # Wait for container to start
    print("\n⏳ Waiting 15 seconds for container to fully start...")
    time.sleep(15)
    
    print("\n" + "=" * 80)
    print("PHASE 2: VERIFICATION")
    print("=" * 80)
    
    # Check if container is running
    if login_data.get('user_id'):
        container_running = check_container_running(username, login_data['user_id'])
    else:
        print("⚠️  No user_id in response, skipping container check")
        container_running = False
    
    # Test if Blender UI is accessible
    if login_data.get('blender_ui_url'):
        ui_accessible = test_blender_ui_accessible(login_data['blender_ui_url'])
    else:
        print("\n⚠️  No Blender UI URL provided, skipping accessibility test")
        ui_accessible = False
    
    print("\n" + "=" * 80)
    print("TEST RESULTS")
    print("=" * 80)
    
    results = {
        "Login successful": bool(login_data),
        "Blender session created": bool(login_data and login_data.get('blender_ui_url')),
        "Container running": container_running,
        "UI accessible": ui_accessible
    }
    
    for test, passed in results.items():
        icon = "✅" if passed else "❌"
        print(f"{icon} {test}")
    
    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED!")
        print(f"\n💡 To access Blender UI, open: {login_data.get('blender_ui_url')}")
        
        # Optionally open in browser
        if login_data.get('blender_ui_url'):
            print("\n🌐 Would you like to open Blender UI in your browser? (y/n)")
            # Auto-open for demonstration
            print("   (Auto-opening in 3 seconds...)")
            time.sleep(3)
            try:
                webbrowser.open(login_data['blender_ui_url'])
                print("   ✅ Browser opened!")
            except Exception as e:
                print(f"   ⚠️  Could not open browser: {e}")
                print(f"   Please manually open: {login_data['blender_ui_url']}")
    else:
        print("\n⚠️  Some tests failed. Check the logs above for details.")
        print("\n🔍 Troubleshooting:")
        if not login_data.get('blender_ui_url'):
            print("   - session_manager might not be initialized in backend")
            print("   - Check backend logs: docker logs prompt2mesh-backend")
        if not container_running:
            print("   - Docker might not be running")
            print("   - Check: docker ps")
        if not ui_accessible:
            print("   - Container might still be starting (wait longer)")
            print("   - Container might have crashed (check logs)")

if __name__ == "__main__":
    main()
