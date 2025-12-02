# EKS Setup Script for Prompt2Mesh
# This script automates the setup process for deploying to EKS

param(
    [Parameter(Mandatory=$false)]
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Prompt2Mesh EKS Setup Script" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""

# Load environment variables from .env file
function Load-EnvFile {
    param([string]$Path)
    
    if (Test-Path $Path) {
        Write-Host "Loading environment variables from $Path..." -ForegroundColor Yellow
        Get-Content $Path | ForEach-Object {
            if ($_ -match '^([^#][^=]+)=(.*)$') {
                $key = $matches[1].Trim()
                $value = $matches[2].Trim()
                [System.Environment]::SetEnvironmentVariable($key, $value, "Process")
                Write-Host "  ✓ $key" -ForegroundColor Green
            }
        }
        Write-Host ""
    } else {
        Write-Host "Error: .env file not found at $Path" -ForegroundColor Red
        exit 1
    }
}

# Load .env file
Load-EnvFile -Path $EnvFile

# Get AWS configuration
$AWS_ACCOUNT_ID = $env:AWS_ACCOUNT_ID
$AWS_REGION = $env:AWS_REGION

if (-not $AWS_ACCOUNT_ID -or $AWS_ACCOUNT_ID -eq "your-aws-account-id") {
    Write-Host "Error: AWS_ACCOUNT_ID not set in .env file" -ForegroundColor Red
    Write-Host "Please update AWS_ACCOUNT_ID in .env file with your AWS account ID" -ForegroundColor Yellow
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

# Step 1: Check prerequisites
Write-Host "Step 1: Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

# Check if AWS CLI is installed
try {
    $awsVersion = aws --version
    Write-Host "  ✓ AWS CLI installed: $awsVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ AWS CLI not found. Please install: https://aws.amazon.com/cli/" -ForegroundColor Red
    exit 1
}

# Check if kubectl is installed
try {
    $kubectlVersion = kubectl version --client --short 2>$null
    Write-Host "  ✓ kubectl installed: $kubectlVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ kubectl not found. Please install: https://kubernetes.io/docs/tasks/tools/" -ForegroundColor Red
    exit 1
}

# Check if Docker is installed
try {
    $dockerVersion = docker --version
    Write-Host "  ✓ Docker installed: $dockerVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Docker not found. Please install Docker Desktop" -ForegroundColor Red
    exit 1
}

Write-Host ""

# Step 2: Login to ECR
Write-Host "Step 2: Logging in to Amazon ECR..." -ForegroundColor Yellow
try {
    $loginCommand = aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"
    Write-Host "  ✓ Successfully logged in to ECR" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to login to ECR. Please check your AWS credentials" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 3: Create ECR repositories
Write-Host "Step 3: Creating ECR repositories..." -ForegroundColor Yellow

$repositories = @("prompt2mesh-backend", "prompt2mesh-streamlit")

foreach ($repo in $repositories) {
    try {
        aws ecr describe-repositories --repository-names $repo --region $AWS_REGION 2>$null | Out-Null
        Write-Host "  ✓ Repository '$repo' already exists" -ForegroundColor Green
    } catch {
        Write-Host "  Creating repository '$repo'..." -ForegroundColor White
        aws ecr create-repository --repository-name $repo --region $AWS_REGION | Out-Null
        Write-Host "  ✓ Repository '$repo' created" -ForegroundColor Green
    }
}
Write-Host ""

# Step 4: Build Docker images
Write-Host "Step 4: Building Docker images..." -ForegroundColor Yellow
Write-Host "  This may take several minutes..." -ForegroundColor White
Write-Host ""

try {
    Write-Host "  Building backend image..." -ForegroundColor White
    docker build -t prompt2mesh-backend:latest -f docker/dockerfile --target backend .
    Write-Host "  ✓ Backend image built successfully" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to build backend image" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Tag and push images to ECR
Write-Host "Step 5: Tagging and pushing images to ECR..." -ForegroundColor Yellow

$backendImageUri = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest"
$streamlitImageUri = "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest"

try {
    Write-Host "  Tagging backend image..." -ForegroundColor White
    docker tag prompt2mesh-backend:latest $backendImageUri
    Write-Host "  ✓ Backend image tagged" -ForegroundColor Green
    
    Write-Host "  Pushing backend image..." -ForegroundColor White
    docker push $backendImageUri
    Write-Host "  ✓ Backend image pushed" -ForegroundColor Green
    
    Write-Host "  Tagging streamlit image..." -ForegroundColor White
    docker tag prompt2mesh-backend:latest $streamlitImageUri
    Write-Host "  ✓ Streamlit image tagged" -ForegroundColor Green
    
    Write-Host "  Pushing streamlit image..." -ForegroundColor White
    docker push $streamlitImageUri
    Write-Host "  ✓ Streamlit image pushed" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Failed to push images to ECR" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 6: Update Kubernetes manifests
Write-Host "Step 6: Updating Kubernetes manifests with ECR image URIs..." -ForegroundColor Yellow

$files = @(
    "k8s\base\backend-deployment.yaml",
    "k8s\base\streamlit-deployment.yaml",
    "k8s\base\db-init-job.yaml",
    "k8s\per-user\user-instance-template.yaml"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        $content = Get-Content $file -Raw
        $content = $content -replace '<AWS_ACCOUNT_ID>', $AWS_ACCOUNT_ID
        $content = $content -replace '<AWS_REGION>', $AWS_REGION
        Set-Content $file -Value $content
        Write-Host "  ✓ Updated $file" -ForegroundColor Green
    }
}
Write-Host ""

# Summary
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Docker images have been built and pushed to ECR:" -ForegroundColor White
Write-Host "  Backend:   $backendImageUri" -ForegroundColor Cyan
Write-Host "  Streamlit: $streamlitImageUri" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update secrets in k8s\base\secrets.yaml with your API keys" -ForegroundColor White
Write-Host "  2. Update domain in k8s\base\ingress.yaml" -ForegroundColor White
Write-Host "  3. Ensure your EKS cluster is running and kubectl is configured" -ForegroundColor White
Write-Host "  4. Deploy to EKS: .\k8s\deploy.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To check your kubectl configuration:" -ForegroundColor Yellow
Write-Host "  kubectl cluster-info" -ForegroundColor Cyan
Write-Host ""
Write-Host "To configure kubectl for your EKS cluster:" -ForegroundColor Yellow
Write-Host "  aws eks update-kubeconfig --name <cluster-name> --region $AWS_REGION" -ForegroundColor Cyan
Write-Host ""
