# Build and push Docker images for Kubernetes deployment
# PowerShell version

param(
    [string]$Registry = "prompt2mesh",
    [string]$Tag = "latest"
)

Write-Host "🐳 Building Docker images..." -ForegroundColor Cyan

# Build backend
Write-Host "📦 Building backend image..." -ForegroundColor Yellow
docker build -f Dockerfile.backend -t "${Registry}/backend:${Tag}" .

# Build frontend
Write-Host "📦 Building frontend image..." -ForegroundColor Yellow
docker build -f Dockerfile.frontend -t "${Registry}/frontend:${Tag}" .

# Build Blender MCP (reuse existing)
Write-Host "📦 Building Blender MCP image..." -ForegroundColor Yellow
Set-Location docker/blender-with-mcp
docker build -t "${Registry}/blender-mcp:${Tag}" .
Set-Location ../..

Write-Host "✅ All images built successfully!" -ForegroundColor Green

# Push to registry (optional)
$push = Read-Host "Push images to registry? (y/N)"
if ($push -eq "y" -or $push -eq "Y") {
    Write-Host "🚀 Pushing images to ${Registry}..." -ForegroundColor Cyan
    docker push "${Registry}/backend:${Tag}"
    docker push "${Registry}/frontend:${Tag}"
    docker push "${Registry}/blender-mcp:${Tag}"
    Write-Host "✅ Images pushed successfully!" -ForegroundColor Green
}

Write-Host ""
Write-Host "📝 Update your k8s/*.yaml files with:" -ForegroundColor Yellow
Write-Host "   Backend image: ${Registry}/backend:${Tag}"
Write-Host "   Frontend image: ${Registry}/frontend:${Tag}"
Write-Host "   Blender image: ${Registry}/blender-mcp:${Tag}"
