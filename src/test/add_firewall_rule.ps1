# Add Windows Firewall rule to allow WSL connections to Blender MCP server
# Run this script as Administrator in PowerShell

$ruleName = "Blender MCP Server (WSL)"
$port = 9876

Write-Host "Adding Windows Firewall rule for Blender MCP..." -ForegroundColor Cyan
Write-Host "Rule Name: $ruleName"
Write-Host "Port: $port"
Write-Host ""

# Remove existing rule if it exists
$existingRule = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
if ($existingRule) {
    Write-Host "Removing existing rule..." -ForegroundColor Yellow
    Remove-NetFirewallRule -DisplayName $ruleName
}

# Add new inbound rule for TCP port 9876
try {
    New-NetFirewallRule -DisplayName $ruleName `
        -Direction Inbound `
        -Protocol TCP `
        -LocalPort $port `
        -Action Allow `
        -Profile Any `
        -Description "Allow WSL and other connections to Blender MCP server on port $port"
    
    Write-Host ""
    Write-Host "Firewall rule added successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Now test the connection from WSL:" -ForegroundColor Cyan
    Write-Host "  python3 test_wsl_to_windows.py" -ForegroundColor White
    Write-Host ""
}
catch {
    Write-Host ""
    Write-Host "Failed to add firewall rule" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you are running PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}
