# ECR Setup Script - Create repositories for all Prompt2Mesh services
# Usage: .\ecr-setup.ps1 -Region <aws-region> -AccountId <aws-account-id>

param(
    [Parameter(Mandatory=$true)]
    [string]$Region,
    
    [Parameter(Mandatory=$true)]
    [string]$AccountId
)

Write-Host "Creating ECR repositories in region: $Region" -ForegroundColor Green
Write-Host "AWS Account ID: $AccountId" -ForegroundColor Green
Write-Host ""

# Array of repository names
$repos = @(
    "prompt2mesh/backend",
    "prompt2mesh/streamlit",
    "prompt2mesh/blender",
    "prompt2mesh/db-init"
)

# Create each repository
foreach ($repo in $repos) {
    Write-Host "Creating repository: $repo" -ForegroundColor Yellow
    
    $output = aws ecr create-repository `
        --repository-name $repo `
        --region $Region `
        --image-scanning-configuration scanOnPush=true `
        --encryption-configuration encryptionType=AES256 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Repository $repo created successfully" -ForegroundColor Green
    }
    elseif ($output -like "*RepositoryAlreadyExistsException*") {
        Write-Host "✓ Repository $repo already exists" -ForegroundColor Cyan
    }
    else {
        Write-Host "✗ Error creating repository $repo" -ForegroundColor Red
        Write-Host "$output" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "ECR repositories setup completed!" -ForegroundColor Green
Write-Host ""
Write-Host "Repository URIs:" -ForegroundColor Yellow
foreach ($repo in $repos) {
    Write-Host "  - $AccountId.dkr.ecr.$Region.amazonaws.com/$repo"
}
