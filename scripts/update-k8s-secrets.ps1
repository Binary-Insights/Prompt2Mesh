# Update Kubernetes Secrets from .env file
# This script helps you update k8s/base/secrets.yaml with values from .env

param(
    [Parameter(Mandatory=$false)]
    [string]$EnvFile = ".env"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================================" -ForegroundColor Cyan
Write-Host "  Update Kubernetes Secrets from .env" -ForegroundColor Cyan
Write-Host "==================================================================" -ForegroundColor Cyan
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

# Read the secrets file
$secretsFile = "k8s\base\secrets.yaml"
if (-not (Test-Path $secretsFile)) {
    Write-Host "Error: secrets.yaml not found at $secretsFile" -ForegroundColor Red
    exit 1
}

# Get values from environment
$POSTGRES_PASSWORD = $env:POSTGRES_PASSWORD
$JWT_SECRET_KEY = $env:JWT_SECRET_KEY
$ANTHROPIC_API_KEY = $env:ANTHROPIC_API_KEY
$LANGCHAIN_API_KEY = $env:LANGCHAIN_API_KEY
$LANGSMITH_API_KEY = $env:LANGSMITH_API_KEY

# Validate required values
if (-not $POSTGRES_PASSWORD) {
    Write-Host "Warning: POSTGRES_PASSWORD not set in .env" -ForegroundColor Yellow
    $POSTGRES_PASSWORD = "postgres"
}

if (-not $JWT_SECRET_KEY -or $JWT_SECRET_KEY -eq "your-super-secret-key-change-this-in-production-12345") {
    Write-Host "Warning: JWT_SECRET_KEY should be changed from default!" -ForegroundColor Yellow
    Write-Host "Generate a secure key with: python -c `"import secrets; print(secrets.token_urlsafe(32))`"" -ForegroundColor Yellow
}

if (-not $ANTHROPIC_API_KEY -or $ANTHROPIC_API_KEY -eq "your-api-key-here") {
    Write-Host "Error: ANTHROPIC_API_KEY not set in .env file" -ForegroundColor Red
    exit 1
}

# Update secrets.yaml
Write-Host "Updating $secretsFile..." -ForegroundColor Yellow

$secretsContent = @"
apiVersion: v1
kind: Secret
metadata:
  name: prompt2mesh-secrets
  namespace: prompt2mesh
type: Opaque
stringData:
  # Updated from .env file on $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
  POSTGRES_PASSWORD: "$POSTGRES_PASSWORD"
  JWT_SECRET_KEY: "$JWT_SECRET_KEY"
  ANTHROPIC_API_KEY: "$ANTHROPIC_API_KEY"
  LANGCHAIN_API_KEY: "$LANGCHAIN_API_KEY"
  LANGSMITH_API_KEY: "$LANGSMITH_API_KEY"
---
# For production, use AWS Secrets Manager or External Secrets Operator
# Example with External Secrets Operator:
# apiVersion: external-secrets.io/v1beta1
# kind: ExternalSecret
# metadata:
#   name: prompt2mesh-secrets
#   namespace: prompt2mesh
# spec:
#   secretStoreRef:
#     name: aws-secrets-manager
#     kind: SecretStore
#   target:
#     name: prompt2mesh-secrets
#   data:
#     - secretKey: ANTHROPIC_API_KEY
#       remoteRef:
#         key: prompt2mesh/anthropic-api-key
#     - secretKey: JWT_SECRET_KEY
#       remoteRef:
#         key: prompt2mesh/jwt-secret-key
"@

Set-Content -Path $secretsFile -Value $secretsContent

Write-Host "Secrets updated successfully" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Cyan
Write-Host "  POSTGRES_PASSWORD: $(if ($POSTGRES_PASSWORD.Length -gt 0) { '*' * $POSTGRES_PASSWORD.Length } else { 'NOT SET' })" -ForegroundColor White
Write-Host "  JWT_SECRET_KEY: $(if ($JWT_SECRET_KEY.Length -gt 0) { '*' * $JWT_SECRET_KEY.Length } else { 'NOT SET' })" -ForegroundColor White
Write-Host "  ANTHROPIC_API_KEY: $(if ($ANTHROPIC_API_KEY.Length -gt 0) { $ANTHROPIC_API_KEY.Substring(0, 10) + '...' } else { 'NOT SET' })" -ForegroundColor White
Write-Host "  LANGCHAIN_API_KEY: $(if ($LANGCHAIN_API_KEY.Length -gt 0) { $LANGCHAIN_API_KEY.Substring(0, 10) + '...' } else { 'NOT SET' })" -ForegroundColor White
Write-Host "  LANGSMITH_API_KEY: $(if ($LANGSMITH_API_KEY.Length -gt 0) { $LANGSMITH_API_KEY.Substring(0, 10) + '...' } else { 'NOT SET' })" -ForegroundColor White
Write-Host ""
Write-Host "WARNING: Do not commit secrets.yaml to version control!" -ForegroundColor Yellow
Write-Host "Add k8s/base/secrets.yaml to .gitignore if not already present" -ForegroundColor Yellow
Write-Host ""
