# Create Kubernetes Secrets for Prompt2Mesh
# Run this script to create secrets before deployment

param(
    [string]$Namespace = "prompt2mesh"
)

Write-Host "Creating Kubernetes Secrets" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

# Check kubectl
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] kubectl not found" -ForegroundColor Red
    exit 1
}

# Check cluster connection
try {
    kubectl cluster-info 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Not connected to Kubernetes cluster" -ForegroundColor Red
        Write-Host "Run: aws eks update-kubeconfig --region us-east-1 --name prompt2mesh-cluster" -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "[ERROR] Not connected to Kubernetes cluster" -ForegroundColor Red
    exit 1
}

# Create namespace if it doesn't exist
Write-Host "Creating namespace: $Namespace" -ForegroundColor Cyan
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f - | Out-Null
Write-Host "[OK] Namespace ready" -ForegroundColor Green
Write-Host ""

# Get secrets from user
Write-Host "Enter the following secrets:" -ForegroundColor Yellow
Write-Host ""

# Database password
Write-Host "1. Database Password (for PostgreSQL):" -ForegroundColor Cyan
$dbPassword = Read-Host "   Enter password" -AsSecureString
$dbPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
)

# JWT secret
Write-Host ""
Write-Host "2. JWT Secret (for authentication - min 32 characters):" -ForegroundColor Cyan
Write-Host "   Leave empty to auto-generate" -ForegroundColor Gray
$jwtInput = Read-Host "   Enter secret (or press Enter)"
if ([string]::IsNullOrWhiteSpace($jwtInput)) {
    # Auto-generate JWT secret
    $jwtSecretPlain = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 64 | ForEach-Object {[char]$_})
    Write-Host "   [OK] Auto-generated JWT secret" -ForegroundColor Green
} else {
    $jwtSecretPlain = $jwtInput
}

# Anthropic API key
Write-Host ""
Write-Host "3. Anthropic API Key:" -ForegroundColor Cyan
$anthropicApiKey = Read-Host "   Enter API key" -AsSecureString
$anthropicApiKeyPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($anthropicApiKey)
)

# Create secret
Write-Host ""
Write-Host "Creating Kubernetes secret..." -ForegroundColor Cyan

kubectl create secret generic api-secrets `
    --namespace=$Namespace `
    --from-literal=DATABASE_PASSWORD=$dbPasswordPlain `
    --from-literal=JWT_SECRET=$jwtSecretPlain `
    --from-literal=ANTHROPIC_API_KEY=$anthropicApiKeyPlain `
    --dry-run=client -o yaml | kubectl apply -f -

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Secrets created successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "Verify secrets:" -ForegroundColor Yellow
    Write-Host "  kubectl get secret api-secrets -n $Namespace" -ForegroundColor White
    Write-Host ""
    Write-Host "View secrets (base64 encoded):" -ForegroundColor Yellow
    Write-Host "  kubectl get secret api-secrets -n $Namespace -o yaml" -ForegroundColor White
} else {
    Write-Host "[ERROR] Failed to create secrets" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[OK] Setup complete! You can now run: .\deploy-to-eks.ps1" -ForegroundColor Green
