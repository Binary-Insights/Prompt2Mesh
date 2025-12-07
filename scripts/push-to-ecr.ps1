# Script to tag and push Docker images to AWS ECR
# Usage: .\push-to-ecr.ps1 -Region <aws-region> -AccountId <aws-account-id>

param(
    [Parameter(Mandatory=$true)]
    [string]$Region,
    
    [Parameter(Mandatory=$true)]
    [string]$AccountId
)

$ECR_REGISTRY = "$AccountId.dkr.ecr.$Region.amazonaws.com"

Write-Host "Authenticating Docker with ECR..." -ForegroundColor Green
aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $ECR_REGISTRY

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Failed to authenticate with ECR" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Tagging and pushing images to ECR..." -ForegroundColor Green
Write-Host ""

# Backend service
Write-Host "Processing backend image..." -ForegroundColor Yellow
docker tag docker-backend:latest "$ECR_REGISTRY/prompt2mesh/backend:latest"
docker push "$ECR_REGISTRY/prompt2mesh/backend:latest"
Write-Host "✓ Backend image pushed" -ForegroundColor Green

# Streamlit service
Write-Host "Processing streamlit image..." -ForegroundColor Yellow
docker tag docker-streamlit:latest "$ECR_REGISTRY/prompt2mesh/streamlit:latest"
docker push "$ECR_REGISTRY/prompt2mesh/streamlit:latest"
Write-Host "✓ Streamlit image pushed" -ForegroundColor Green

# DB Init service
Write-Host "Processing db-init image..." -ForegroundColor Yellow
docker tag docker-db-init:latest "$ECR_REGISTRY/prompt2mesh/db-init:latest"
docker push "$ECR_REGISTRY/prompt2mesh/db-init:latest"
Write-Host "✓ DB-init image pushed" -ForegroundColor Green

# Blender service (using linuxserver image - optional, for reference)
Write-Host "Processing blender image..." -ForegroundColor Yellow
docker pull linuxserver/blender:latest
docker tag linuxserver/blender:latest "$ECR_REGISTRY/prompt2mesh/blender:latest"
docker push "$ECR_REGISTRY/prompt2mesh/blender:latest"
Write-Host "✓ Blender image pushed" -ForegroundColor Green

Write-Host ""
Write-Host "All images successfully pushed to ECR!" -ForegroundColor Green
Write-Host ""
Write-Host "Image URIs:" -ForegroundColor Yellow
Write-Host "  - $ECR_REGISTRY/prompt2mesh/backend:latest"
Write-Host "  - $ECR_REGISTRY/prompt2mesh/streamlit:latest"
Write-Host "  - $ECR_REGISTRY/prompt2mesh/db-init:latest"
Write-Host "  - $ECR_REGISTRY/prompt2mesh/blender:latest"
