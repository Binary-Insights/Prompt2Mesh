# Update Kubernetes manifests with correct ECR image URIs
# This script updates the image URIs in all Kubernetes deployment files

param(
    [Parameter(Mandatory=$false)]
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Update Kubernetes Manifests with ECR Image URIs" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env file
if (Test-Path $EnvFile) {
    Write-Host "Loading environment variables from $EnvFile..." -ForegroundColor Yellow
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match '^([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
    Write-Host "Environment variables loaded successfully" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Error: .env file not found at $EnvFile" -ForegroundColor Red
    exit 1
}

# Get AWS configuration
$AWS_ACCOUNT_ID = $env:AWS_ACCOUNT_ID
$AWS_REGION = $env:AWS_REGION

if (-not $AWS_ACCOUNT_ID) {
    Write-Host "Error: AWS_ACCOUNT_ID not set in .env file" -ForegroundColor Red
    exit 1
}

if (-not $AWS_REGION) {
    Write-Host "Warning: AWS_REGION not set, using default us-east-1" -ForegroundColor Yellow
    $AWS_REGION = "us-east-1"
}

Write-Host "AWS Configuration:" -ForegroundColor Cyan
Write-Host "  Account ID: $AWS_ACCOUNT_ID" -ForegroundColor White
Write-Host "  Region: $AWS_REGION" -ForegroundColor White
Write-Host ""

# Files to update
$files = @(
    "k8s\base\backend-deployment.yaml",
    "k8s\base\streamlit-deployment.yaml",
    "k8s\base\db-init-job.yaml",
    "k8s\per-user\user-instance-template.yaml"
)

Write-Host "Updating Kubernetes manifests..." -ForegroundColor Yellow
Write-Host ""

$updated = 0
foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        
        # Replace placeholders with actual values
        $originalContent = $content
        $content = $content -replace '<AWS_ACCOUNT_ID>', $AWS_ACCOUNT_ID
        $content = $content -replace '<AWS_REGION>', $AWS_REGION
        
        if ($content -ne $originalContent) {
            Set-Content $file -Value $content -NoNewline
            Write-Host "  Updated: $file" -ForegroundColor Green
            $updated++
        } else {
            Write-Host "  No changes needed: $file" -ForegroundColor Gray
        }
    } else {
        Write-Host "  Not found: $file" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "  Update Complete!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  Files updated: $updated" -ForegroundColor White
Write-Host "  ECR Registry: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com" -ForegroundColor White
Write-Host ""
Write-Host "Image URIs now configured as:" -ForegroundColor Cyan
Write-Host "  Backend: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest" -ForegroundColor White
Write-Host "  Streamlit: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest" -ForegroundColor White
Write-Host ""
