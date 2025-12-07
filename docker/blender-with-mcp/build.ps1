# Build script for custom Blender image with MCP addon

Write-Host "🔨 Building custom Blender image with MCP addon..." -ForegroundColor Cyan

# Create build context directory
$buildDir = "C:\Prompt2Mesh\docker\blender-with-mcp"
Set-Location $buildDir

# Copy files to build context
Write-Host "📦 Copying files to build context..." -ForegroundColor Yellow
Copy-Item "C:\Prompt2Mesh\src\addon\addon.py" -Destination "blender_mcp_addon.py" -Force

# Build the image
Write-Host "🐳 Building Docker image..." -ForegroundColor Yellow
docker build -t prompt2mesh/blender-mcp:latest .

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Image built successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📝 Next steps:" -ForegroundColor Cyan
    Write-Host "   1. Restart backend: docker-compose restart backend"
    Write-Host "   2. Test with: python test_e2e.py"
} else {
    Write-Host "❌ Build failed!" -ForegroundColor Red
    exit 1
}
