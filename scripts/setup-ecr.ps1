# Setup ECR Repositories for Prompt2Mesh
# This script creates ECR repositories for all container images

param(
    [string]$Region = "us-east-1",
    [string]$Prefix = "prompt2mesh"
)

Write-Host "Setting up ECR repositories" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Prefix: $Prefix" -ForegroundColor Yellow
Write-Host ""

# Check AWS CLI
if (!(Get-Command aws -ErrorAction SilentlyContinue)) {
    Write-Host "❌ AWS CLI not installed" -ForegroundColor Red
    exit 1
}

# Get AWS account ID
Write-Host "Getting AWS account ID..." -ForegroundColor Cyan
try {
    $accountId = (aws sts get-caller-identity --query Account --output text)
    Write-Host "[OK] Account ID: $accountId" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to get AWS account ID" -ForegroundColor Red
    exit 1
}

$repositories = @("backend", "frontend", "blender-mcp")

Write-Host ""
Write-Host "Creating ECR repositories..." -ForegroundColor Cyan

$registryUrl = "$accountId.dkr.ecr.$Region.amazonaws.com"
$createdRepos = @{}

foreach ($repo in $repositories) {
    $repoName = "$Prefix/$repo"
    Write-Host "  Creating: $repoName..." -ForegroundColor Yellow
    
    # Check if repository exists
    $exists = aws ecr describe-repositories --region $Region --repository-names $repoName 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [INFO] Repository already exists" -ForegroundColor Blue
    } else {
        # Create repository
        aws ecr create-repository `
            --region $Region `
            --repository-name $repoName `
            --image-scanning-configuration scanOnPush=true `
            --encryption-configuration encryptionType=AES256 `
            --tags Key=Project,Value=Prompt2Mesh Key=ManagedBy,Value=Script | Out-Null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "    [OK] Created successfully" -ForegroundColor Green
        } else {
            Write-Host "    [ERROR] Failed to create repository" -ForegroundColor Red
            continue
        }
    }
    
    # Set lifecycle policy to keep only last 10 images
    $lifecyclePolicy = @"
{
  "rules": [
    {
      "rulePriority": 1,
      "description": "Keep only last 10 images",
      "selection": {
        "tagStatus": "any",
        "countType": "imageCountMoreThan",
        "countNumber": 10
      },
      "action": {
        "type": "expire"
      }
    }
  ]
}
"@
    
    $lifecyclePolicy | aws ecr put-lifecycle-policy `
        --region $Region `
        --repository-name $repoName `
        --lifecycle-policy-text file:///dev/stdin | Out-Null
    
    $imageUri = "$registryUrl/$repoName"
    $createdRepos[$repo] = $imageUri
    Write-Host "    URI: $imageUri" -ForegroundColor White
}

Write-Host ""
Write-Host "[OK] ECR repositories created successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "Repository URIs:" -ForegroundColor Yellow
foreach ($key in $createdRepos.Keys) {
    Write-Host "  $key : $($createdRepos[$key])" -ForegroundColor White
}

# Save to config file
$config = @{
    registry_url = $registryUrl
    account_id = $accountId
    region = $Region
    repositories = $createdRepos
} | ConvertTo-Json -Depth 10

$configPath = ".\ecr-config.json"
$config | Out-File -FilePath $configPath -Encoding UTF8

Write-Host ""
Write-Host "[OK] Configuration saved to: $configPath" -ForegroundColor Green

Write-Host ""
Write-Host "To authenticate Docker with ECR, run:" -ForegroundColor Yellow
Write-Host "  aws ecr get-login-password --region $Region | docker login --username AWS --password-stdin $registryUrl" -ForegroundColor White

Write-Host ""
Write-Host "Next step:" -ForegroundColor Yellow
Write-Host "  Run: .\build-and-push-images.ps1" -ForegroundColor White
