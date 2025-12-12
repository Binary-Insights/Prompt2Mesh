"""
Simple direct test of Blender connection
Sends a basic command and waits for response
"""
import socket
import json
import sys

HOST = "localhost"
PORT = 9876

def test_connection():
    print(f"Connecting to {HOST}:{PORT}...")
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30.0)
    
    try:
        sock.connect((HOST, PORT))
        print("✓ Connected!")
        
        # Send a simple command
        command = {
            "type": "get_scene_info",
            "params": {}
        }
        
        print(f"\nSending: {json.dumps(command)}")
        sock.sendall(json.dumps(command).encode('utf-8'))
        
        print("\nWaiting for response (30 second timeout)...")
        
        # Try to receive response
        chunks = []
        while True:
            try:
                chunk = sock.recv(8192)
                if not chunk:
                    print("Connection closed by server")
                    break
                
                print(f"Received chunk: {len(chunk)} bytes")
                chunks.append(chunk)
                
                # Try to parse
                try:
                    data = b''.join(chunks)
                    response = json.loads(data.decode('utf-8'))
                    print("\n✓ Got complete response:")
                    print(json.dumps(response, indent=2))
                    return
                except json.JSONDecodeError:
                    print("  (incomplete JSON, waiting for more...)")
                    continue
                    
            except socket.timeout:
                print("\n✗ Timeout waiting for response")
                if chunks:
                    data = b''.join(chunks)
                    print(f"Partial data received: {data[:200]}")
                break
                
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sock.close()

if __name__ == "__main__":
    test_connection()
