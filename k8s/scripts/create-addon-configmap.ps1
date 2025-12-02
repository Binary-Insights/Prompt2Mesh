# PowerShell script to create ConfigMap with Blender addon
# This embeds the addon.py file content into a Kubernetes ConfigMap

# Get the project root directory (go up two levels from scripts directory)
$scriptDir = Split-Path -Parent $PSCommandPath
$projectRoot = Split-Path -Parent (Split-Path -Parent $scriptDir)

$addonPath = Join-Path $projectRoot "src\addon\addon.py"
$serverScriptPath = Join-Path $projectRoot "k8s\scripts\start_mcp_server.py"
$outputPath = Join-Path $projectRoot "k8s\base\blender-addon-configmap.yaml"

Write-Host "Creating Blender addon ConfigMap..." -ForegroundColor Green
Write-Host "Project root: $projectRoot"

# Read the addon file
if (!(Test-Path $addonPath)) {
    Write-Host "Error: $addonPath not found!" -ForegroundColor Red
    exit 1
}

# Read the MCP server script
if (!(Test-Path $serverScriptPath)) {
    Write-Host "Error: $serverScriptPath not found!" -ForegroundColor Red
    exit 1
}

$addonContent = Get-Content $addonPath -Raw
$serverScript = Get-Content $serverScriptPath -Raw

# Indent addon content
$indentedAddon = ($addonContent -split "`n" | ForEach-Object { "    $_" }) -join "`n"

# Indent server script
$indentedServer = ($serverScript -split "`n" | ForEach-Object { "    $_" }) -join "`n"

# Create the enable script
$enableScript = @'
    #!/usr/bin/env python3
    import bpy
    import sys
    import time
    
    def enable_addon():
        addon_name = "blender_mcp_addon"
        try:
            bpy.ops.preferences.addon_enable(module=addon_name)
            bpy.ops.wm.save_userpref()
            print("Enabled addon")
            
            if hasattr(bpy.types, 'blendermcp_server'):
                if bpy.types.blendermcp_server is None:
                    import importlib
                    addon_module = importlib.import_module('blender_mcp_addon')
                    bpy.types.blendermcp_server = addon_module.BlenderMCPServer(host='0.0.0.0', port=9876)
                bpy.types.blendermcp_server.start()
                bpy.context.scene.blendermcp_server_running = True
                print("MCP server started on 0.0.0.0:9876")
            return True
        except Exception as e:
            print("Failed: " + str(e))
            import traceback
            traceback.print_exc()
            return False
    
    if __name__ == "__main__":
        time.sleep(2)
        enable_addon()
'@

# Build the YAML manually
$yaml = "apiVersion: v1`nkind: ConfigMap`nmetadata:`n  name: blender-addon-scripts`n  namespace: prompt2mesh`ndata:`n  addon.py: |`n"
$yaml += $indentedAddon
$yaml += "`n  enable_addon.py: |`n"
$yaml += $enableScript
$yaml += "`n  start_mcp_server.py: |`n"
$yaml += $indentedServer

# Write to file
$yaml | Out-File -FilePath $outputPath -Encoding utf8 -NoNewline

Write-Host "ConfigMap created successfully at: $outputPath" -ForegroundColor Green
Write-Host "File size: $((Get-Item $outputPath).Length / 1KB) KB" -ForegroundColor Cyan
$size = [math]::Round((Get-Item $outputPath).Length / 1KB, 2)
Write-Host "ConfigMap size: $size KB" -ForegroundColor Cyan
