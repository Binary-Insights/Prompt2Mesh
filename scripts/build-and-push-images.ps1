# Build and Push Images to ECR
# This script builds Docker images and pushes them to ECR

param(
    [string]$ConfigFile = ".\ecr-config.json",
    [string]$Tag = "latest"
)

Write-Host "Building and pushing Docker images to ECR" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker..." -ForegroundColor Cyan
try {
    docker info | Out-Null
    Write-Host "[OK] Docker is running" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop." -ForegroundColor Red
    exit 1
}

# Load ECR config
if (!(Test-Path $ConfigFile)) {
    Write-Host "[ERROR] ECR config not found: $ConfigFile" -ForegroundColor Red
    Write-Host "Run: .\setup-ecr.ps1" -ForegroundColor Yellow
    exit 1
}

Write-Host "Loading ECR configuration..." -ForegroundColor Cyan
$config = Get-Content $ConfigFile | ConvertFrom-Json
$registryUrl = $config.registry_url
$region = $config.region

Write-Host "[OK] Configuration loaded" -ForegroundColor Green
Write-Host "   Registry: $registryUrl" -ForegroundColor White
Write-Host "   Region: $region" -ForegroundColor White
Write-Host ""

# Login to ECR
Write-Host "Authenticating with ECR..." -ForegroundColor Cyan
aws ecr get-login-password --region $region | docker login --username AWS --password-stdin $registryUrl

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to authenticate with ECR" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] Authenticated successfully" -ForegroundColor Green
Write-Host ""

# Build and push images
$images = @{
    "backend" = @{
        dockerfile = "Dockerfile.backend"
        context = "."
    }
    "frontend" = @{
        dockerfile = "Dockerfile.frontend"
        context = "."
    }
    "blender-mcp" = @{
        dockerfile = "docker/dockerfile"
        context = "docker"
    }
}

foreach ($imageName in $images.Keys) {
    $imageConfig = $images[$imageName]
    $repoUri = $config.repositories.$imageName
    $fullTag = "${repoUri}:${Tag}"
    
    Write-Host "Building $imageName..." -ForegroundColor Cyan
    Write-Host "   Dockerfile: $($imageConfig.dockerfile)" -ForegroundColor White
    Write-Host "   Context: $($imageConfig.context)" -ForegroundColor White
    Write-Host "   Tag: $fullTag" -ForegroundColor White
    
    # Build image
    docker build `
        -f $imageConfig.dockerfile `
        -t $fullTag `
        $imageConfig.context
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to build $imageName" -ForegroundColor Red
        continue
    }
    
    Write-Host "[OK] Built successfully" -ForegroundColor Green
    
    # Push image
    Write-Host "Pushing $imageName to ECR..." -ForegroundColor Cyan
    docker push $fullTag
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to push $imageName" -ForegroundColor Red
        continue
    }
    
    Write-Host "[OK] Pushed successfully" -ForegroundColor Green
    Write-Host ""
}

Write-Host "[OK] All images built and pushed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Update your k8s manifests with these image URIs:" -ForegroundColor Yellow
foreach ($key in $config.repositories.PSObject.Properties.Name) {
    Write-Host "  $key : $($config.repositories.$key):$Tag" -ForegroundColor White
}

Write-Host ""
Write-Host "Next step:" -ForegroundColor Yellow
Write-Host "  Run: .\update-k8s-manifests.ps1" -ForegroundColor White
