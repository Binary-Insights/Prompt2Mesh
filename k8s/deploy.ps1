# PowerShell deployment script for Prompt2Mesh to EKS

$ErrorActionPreference = "Stop"

Write-Host "Deploying Prompt2Mesh to EKS..." -ForegroundColor Green

# Create namespace
Write-Host "Creating namespace..." -ForegroundColor Yellow
kubectl apply -f k8s/base/namespace.yaml

# Apply secrets and config
Write-Host "Applying secrets and config..." -ForegroundColor Yellow
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/configmap.yaml

# Deploy PostgreSQL
Write-Host "Deploying PostgreSQL..." -ForegroundColor Yellow
kubectl apply -f k8s/base/postgres-pvc.yaml
kubectl apply -f k8s/base/postgres-deployment.yaml

# Wait for postgres
Write-Host "Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s

# Initialize database
Write-Host "Initializing database..." -ForegroundColor Yellow
kubectl apply -f k8s/base/db-init-job.yaml
kubectl wait --for=condition=complete job/db-init -n prompt2mesh --timeout=300s

# Deploy backend
Write-Host "Deploying backend..." -ForegroundColor Yellow
kubectl apply -f k8s/base/backend-deployment.yaml

# Deploy frontend
Write-Host "Deploying Streamlit frontend..." -ForegroundColor Yellow
kubectl apply -f k8s/base/streamlit-deployment.yaml

# Deploy Blender (optional shared instance)
Write-Host "Deploying Blender..." -ForegroundColor Yellow
kubectl apply -f k8s/base/blender-deployment.yaml

# Deploy ingress
Write-Host "Deploying ingress..." -ForegroundColor Yellow
kubectl apply -f k8s/base/ingress.yaml

Write-Host ""
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Check status with:" -ForegroundColor Cyan
Write-Host "  kubectl get pods -n prompt2mesh" -ForegroundColor White
Write-Host ""
Write-Host "Get ALB DNS name with:" -ForegroundColor Cyan
Write-Host "  kubectl get ingress prompt2mesh-ingress -n prompt2mesh" -ForegroundColor White
