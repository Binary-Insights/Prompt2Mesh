# WSL to Windows Blender Connection - Setup Complete ✓

## Summary

Successfully enabled WSL to connect to Windows Blender MCP server.

## What Was Fixed

1. **Blender Addon Response Issue (FIXED)**
   - Modified `addon.py` to use `threading.Event` for synchronous response handling
   - Changed binding from `localhost` to `0.0.0.0` to accept external connections

2. **WSL Network Configuration (FIXED)**
   - Identified correct Windows IP: `172.24.96.1` (WSL vEthernet interface)
   - Created Python-based port forwarder (more stable than socat)
   - Added Windows Firewall rules to allow WSL connections

3. **Port Forwarder (WORKING)**
   - `wsl_port_forward.py` - Forwards `localhost:9876` (WSL) → `172.24.96.1:9876` (Windows)
   - Auto-detects correct Windows IP address
   - Handles bidirectional data flow properly

## How to Use

### From Windows PowerShell (Direct Connection)
```powershell
cd C:\Users\enigm\OneDrive\Documents\NortheasternAssignments\09_BigDataIntelAnlytics\Assignments\Prompt2Mesh
python interactive_client.py
```

### From WSL (Via Port Forwarder)

**Terminal 1 - Start Port Forwarder:**
```bash
cd /mnt/c/Users/enigm/OneDrive/Documents/NortheasternAssignments/09_BigDataIntelAnlytics/Assignments/Prompt2Mesh
python3 wsl_port_forward.py
```

**Terminal 2 - Run Interactive Client:**
```bash
BLENDER_USE_LOCALHOST=1 python interactive_client.py
```

## Files Created/Modified

### New Files
- `wsl_port_forward.py` - Python-based port forwarder (replaces socat)
- `start_wsl_forward.sh` - Helper script to start forwarder
- `add_firewall_rule.ps1` - Windows Firewall configuration
- `test_wsl_to_windows.py` - Connection testing utility
- `find_windows_ip.py` - IP detection utility
- `test_windows.py` - Direct Windows connection test

### Modified Files
- `addon.py` - Added threading.Event synchronization and 0.0.0.0 binding
- `interactive_client.py` - Auto-detects WSL and uses appropriate connection method

## Network Configuration

- **Blender Server**: Listening on `0.0.0.0:9876` (Windows)
- **WSL vEthernet IP**: `172.24.96.1`
- **Port Forwarder**: WSL `localhost:9876` → Windows `172.24.96.1:9876`
- **Firewall Rules**: Inbound TCP port 9876 allowed

## Troubleshooting

### If connection fails from WSL:

1. **Check if Blender server is running:**
   ```powershell
   netstat -ano | findstr "9876"
   ```

2. **Check if port forwarder is running:**
   ```bash
   lsof -i :9876
   ```

3. **Test direct connection:**
   ```bash
   python3 find_windows_ip.py
   ```

4. **Restart everything:**
   - Stop Blender server (in Blender: BlenderMCP panel)
   - Kill port forwarder: `pkill -f wsl_port_forward.py`
   - Start Blender server
   - Start port forwarder: `python3 wsl_port_forward.py`

## Status: ✅ WORKING

Both Windows and WSL can now successfully connect to and control Blender!
