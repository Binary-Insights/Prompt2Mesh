# Prompt2Mesh Setup Guide

## Overview
Prompt2Mesh is an MCP (Model Context Protocol) server that allows AI assistants to control Blender. It consists of two components:
1. **Blender Addon**: Runs inside Blender and listens for commands on port 9876
2. **MCP Server**: Bridges MCP clients (like Claude) to the Blender addon

## Setup Instructions

### 1. Install the Blender Addon

1. **Open Blender**
2. Go to **Edit → Preferences → Add-ons**
3. Click **Install** button
4. Navigate to and select `addon.py` from this directory
5. Enable the **"Blender MCP"** addon by checking the checkbox
6. The addon panel will appear in the 3D View sidebar (press `N` to show sidebar)

### 2. Start the Blender Server

1. In Blender's 3D View, press `N` to open the sidebar
2. Click on the **"BlenderMCP"** tab
3. Click the **"Start Server"** button
4. The server will start listening on port 9876 (default)
5. You should see "Server running" status

### 3. Run the MCP Server

In your terminal with the virtual environment activated:

```bash
# Make sure you're in the Prompt2Mesh directory
cd c:\Users\enigm\OneDrive\Documents\NortheasternAssignments\09_BigDataIntelAnlytics\Assignments\Prompt2Mesh

# Activate virtual environment (if not already active)
.\.venv\Scripts\Activate.ps1

# Run the MCP server
python main.py
```

The MCP server will:
- Start up and connect to Blender on port 9876
- Listen for MCP client connections via stdio
- Forward commands between the MCP client and Blender

### 4. Configure Your MCP Client

#### For Claude Desktop:

Add this to your Claude Desktop config file (`claude_desktop_config.json`):

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "blender": {
      "command": "python",
      "args": [
        "c:\\Users\\enigm\\OneDrive\\Documents\\NortheasternAssignments\\09_BigDataIntelAnlytics\\Assignments\\Prompt2Mesh\\main.py"
      ],
      "env": {
        "PYTHONPATH": "c:\\Users\\enigm\\OneDrive\\Documents\\NortheasternAssignments\\09_BigDataIntelAnlytics\\Assignments\\Prompt2Mesh\\.venv\\Lib\\site-packages"
      }
    }
  }
}
```

#### For VS Code with Cline:

Add to your MCP settings in Cline configuration.

### 5. Test the Connection

Use the provided test client to verify everything works:

```bash
python test_blender_connection.py
```

## Troubleshooting

### "Connection refused" error:
- **Cause**: Blender addon server is not running
- **Fix**: Start the server in Blender (see step 2 above)

### "Invalid JSON" error when typing commands:
- **Cause**: The MCP server expects JSON-RPC formatted messages from an MCP client, not direct text input
- **Fix**: Use an MCP client (Claude Desktop, Cline, etc.) or the test client

### Port already in use:
- **Cause**: Another instance of the Blender server is running
- **Fix**: Stop the server in Blender, or change the port in both the addon and server config

## Usage

Once everything is set up, you can use natural language through your MCP client:

- "Create a red sphere at the origin"
- "Add a UV sphere and apply gravity physics to it"
- "Import a 3D model from Sketchfab"
- "Render the current scene"

The MCP server will translate these requests into Blender commands.

## Architecture

```
┌─────────────────┐
│  MCP Client     │
│  (Claude/Cline) │
└────────┬────────┘
         │ JSON-RPC via stdio
         ▼
┌─────────────────┐
│  MCP Server     │
│  (main.py)      │
└────────┬────────┘
         │ TCP Socket (port 9876)
         ▼
┌─────────────────┐
│  Blender Addon  │
│  (addon.py)     │
└─────────────────┘
```
