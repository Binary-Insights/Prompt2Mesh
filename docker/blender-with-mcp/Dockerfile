FROM linuxserver/blender:latest

# Set working directory
WORKDIR /app

# Copy MCP addon to default Blender directories
COPY blender_mcp_addon.py /defaults/.config/blender/4.2/scripts/addons/blender_mcp_addon.py
COPY blender_mcp_addon.py /defaults/.config/blender/5.0/scripts/addons/blender_mcp_addon.py

# Copy init script to setup addon
COPY 99-mcp-addon-setup /etc/cont-init.d/99-mcp-addon-setup
RUN chmod +x /etc/cont-init.d/99-mcp-addon-setup

# Expose MCP server port
EXPOSE 9876

# Expose Blender UI ports
EXPOSE 3000 3001
