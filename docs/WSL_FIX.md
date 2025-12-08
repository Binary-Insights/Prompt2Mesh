# WSL Connection Guide

## The Problem

The Blender addon was binding to `localhost` (127.0.0.1), which is only accessible from Windows itself, not from WSL.

## The Fix

The addon has been updated to bind to `0.0.0.0` (all network interfaces), allowing WSL to connect.

## Steps to Apply

### 1. Restart the Blender Server

In Blender:
1. Go to the **BlenderMCP** panel (press `N` in 3D View)
2. Click **"Stop Server"** if it's running
3. Click **"Start Server"** again

The server will now accept connections from both Windows and WSL.

### 2. Test from WSL

```bash
python interactive_client.py
```

You should now see:
```
🐧 Running in WSL - connecting to Windows host: 10.255.255.254
✓ Connected to Blender at 10.255.255.254:9876
```

## Alternative: Manual Port Forwarding (If needed)

If you can't restart Blender or prefer not to change the addon:

```bash
# Run this in WSL
chmod +x setup_wsl_forward.sh
./setup_wsl_forward.sh
```

This creates a port forward using `socat`, then connect to `localhost:9876` from WSL.

## Security Note

Binding to `0.0.0.0` means the Blender server accepts connections from any network interface. This is safe for:
- Local development
- When behind a firewall
- WSL/local network only access

If you're concerned, you can use the port forwarding method instead.
