# Update Kubernetes manifests with ECR image URIs
# This script updates all k8s YAML files with the correct image URIs

param(
    [string]$ConfigFile = ".\ecr-config.json",
    [string]$Tag = "latest"
)

Write-Host "Updating Kubernetes manifests with ECR image URIs" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Load ECR config
if (!(Test-Path $ConfigFile)) {
    Write-Host "[ERROR] ECR config not found: $ConfigFile" -ForegroundColor Red
    Write-Host "Run: .\setup-ecr.ps1" -ForegroundColor Yellow
    exit 1
}

$config = Get-Content $ConfigFile | ConvertFrom-Json

# Image URIs
$backendImage = "$($config.repositories.backend):$Tag"
$frontendImage = "$($config.repositories.frontend):$Tag"
$blenderImage = "$($config.repositories.'blender-mcp'):$Tag"

Write-Host "Image URIs:" -ForegroundColor Yellow
Write-Host "  Backend: $backendImage" -ForegroundColor White
Write-Host "  Frontend: $frontendImage" -ForegroundColor White
Write-Host "  Blender: $blenderImage" -ForegroundColor White
Write-Host ""

# Update backend-deployment.yaml
Write-Host "Updating k8s/backend-deployment.yaml..." -ForegroundColor Cyan
$backendYaml = Get-Content ".\k8s\backend-deployment.yaml" -Raw
$backendYaml = $backendYaml -replace 'image: prompt2mesh/backend:.*', "image: $backendImage"
$backendYaml | Out-File ".\k8s\backend-deployment.yaml" -Encoding UTF8 -NoNewline
Write-Host "[OK] Updated backend deployment" -ForegroundColor Green

# Update frontend-deployment.yaml
Write-Host "Updating k8s/frontend-deployment.yaml..." -ForegroundColor Cyan
$frontendYaml = Get-Content ".\k8s\frontend-deployment.yaml" -Raw
$frontendYaml = $frontendYaml -replace 'image: prompt2mesh/frontend:.*', "image: $frontendImage"
$frontendYaml | Out-File ".\k8s\frontend-deployment.yaml" -Encoding UTF8 -NoNewline
Write-Host "[OK] Updated frontend deployment" -ForegroundColor Green

# Update k8s_user_session_manager.py
Write-Host "Updating src/backend/k8s_user_session_manager.py..." -ForegroundColor Cyan
$managerPy = Get-Content ".\src\backend\k8s_user_session_manager.py" -Raw
$managerPy = $managerPy -replace 'image="prompt2mesh/blender-mcp:.*"', "image=`"$blenderImage`""
$managerPy | Out-File ".\src\backend\k8s_user_session_manager.py" -Encoding UTF8 -NoNewline
Write-Host "[OK] Updated session manager" -ForegroundColor Green

Write-Host ""
Write-Host "[OK] All manifests updated successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Next step:" -ForegroundColor Yellow
Write-Host "  Run: .\deploy-to-eks.ps1" -ForegroundColor White
