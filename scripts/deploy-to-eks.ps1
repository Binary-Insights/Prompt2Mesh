# Deploy Prompt2Mesh to EKS
# Complete deployment script that applies all Kubernetes resources

param(
    [string]$Namespace = "prompt2mesh",
    [string]$ConfigFile = ".\ecr-config.json"
)

Write-Host "Deploying Prompt2Mesh to EKS" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan
Write-Host "Namespace: $Namespace" -ForegroundColor Yellow
Write-Host ""

# Check kubectl
Write-Host "Checking prerequisites..." -ForegroundColor Cyan
if (!(Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl not installed" -ForegroundColor Red
    exit 1
}

# Verify cluster connection
Write-Host "Verifying cluster connection..." -ForegroundColor Cyan
try {
    $clusterInfo = kubectl cluster-info 2>&1
    Write-Host "[OK] Connected to cluster" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Not connected to cluster" -ForegroundColor Red
    Write-Host "Run: aws eks update-kubeconfig --region <region> --name <cluster-name>" -ForegroundColor Yellow
    exit 1
}

# Create namespace
Write-Host ""
Write-Host "Creating namespace..." -ForegroundColor Cyan
kubectl create namespace $Namespace --dry-run=client -o yaml | kubectl apply -f -

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Namespace ready: $Namespace" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to create namespace" -ForegroundColor Red
    exit 1
}

# Apply StorageClass
Write-Host ""
Write-Host "Setting up StorageClass..." -ForegroundColor Cyan
kubectl apply -f .\k8s\storageclass.yaml

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] StorageClass configured" -ForegroundColor Green
} else {
    Write-Host "[WARNING] StorageClass setup failed (may already exist)" -ForegroundColor Yellow
}

# Create secrets (interactive)
Write-Host ""
Write-Host "Setting up secrets..." -ForegroundColor Cyan
Write-Host "Enter the following secrets:" -ForegroundColor Yellow

$dbPassword = Read-Host "Database password (for PostgreSQL)" -AsSecureString
$jwtSecret = Read-Host "JWT secret (for authentication)" -AsSecureString
$anthropicApiKey = Read-Host "Anthropic API key" -AsSecureString

# Convert secure strings
$dbPasswordPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($dbPassword)
)
$jwtSecretPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($jwtSecret)
)
$anthropicApiKeyPlain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($anthropicApiKey)
)

# Create secret
kubectl create secret generic api-secrets `
    --namespace=$Namespace `
    --from-literal=DATABASE_PASSWORD=$dbPasswordPlain `
    --from-literal=JWT_SECRET=$jwtSecretPlain `
    --from-literal=ANTHROPIC_API_KEY=$anthropicApiKeyPlain `
    --dry-run=client -o yaml | kubectl apply -f -

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Secrets created" -ForegroundColor Green
} else {
    Write-Host "[ERROR] Failed to create secrets" -ForegroundColor Red
    exit 1
}

# Apply RBAC
Write-Host ""
Write-Host "Applying RBAC configuration..." -ForegroundColor Cyan
kubectl apply -f .\k8s\rbac.yaml -n $Namespace

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] RBAC configured" -ForegroundColor Green
} else {
    Write-Host "[ERROR] RBAC setup failed" -ForegroundColor Red
    exit 1
}

# Deploy PostgreSQL
Write-Host ""
Write-Host "Deploying PostgreSQL..." -ForegroundColor Cyan
kubectl apply -f .\k8s\postgres-deployment.yaml -n $Namespace

Write-Host "   Waiting for PostgreSQL to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=postgres -n $Namespace --timeout=300s

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] PostgreSQL ready" -ForegroundColor Green
} else {
    Write-Host "[WARNING] PostgreSQL may still be starting..." -ForegroundColor Yellow
}

# Initialize database
Write-Host ""
Write-Host "Initializing database schema..." -ForegroundColor Cyan
Write-Host "   Note: Run init_db.py manually after backend is running" -ForegroundColor Yellow

# Deploy Backend
Write-Host ""
Write-Host "Deploying Backend..." -ForegroundColor Cyan
kubectl apply -f .\k8s\backend-deployment.yaml -n $Namespace

Write-Host "   Waiting for backend to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=backend -n $Namespace --timeout=300s

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Backend ready" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Backend may still be starting..." -ForegroundColor Yellow
}

# Deploy Frontend
Write-Host ""
Write-Host "Deploying Frontend..." -ForegroundColor Cyan
kubectl apply -f .\k8s\frontend-deployment.yaml -n $Namespace

Write-Host "   Waiting for frontend to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=ready pod -l app=frontend -n $Namespace --timeout=300s

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Frontend ready" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Frontend may still be starting..." -ForegroundColor Yellow
}

# Get service status
Write-Host ""
Write-Host "Deployment Status:" -ForegroundColor Cyan
kubectl get pods -n $Namespace
Write-Host ""
kubectl get svc -n $Namespace

# Get LoadBalancer URL
Write-Host ""
Write-Host "Getting Frontend URL..." -ForegroundColor Cyan
$frontendUrl = kubectl get svc frontend -n $Namespace -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null

if ($frontendUrl) {
    Write-Host "[OK] Frontend accessible at: http://${frontendUrl}:8501" -ForegroundColor Green
} else {
    Write-Host "[WAIT] LoadBalancer provisioning... Check with:" -ForegroundColor Yellow
    Write-Host "   kubectl get svc frontend -n $Namespace" -ForegroundColor White
}

Write-Host ""
Write-Host "[OK] Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Useful commands:" -ForegroundColor Yellow
Write-Host "  View pods:           kubectl get pods -n $Namespace" -ForegroundColor White
Write-Host "  View logs (backend): kubectl logs -f deployment/backend -n $Namespace" -ForegroundColor White
Write-Host "  View logs (frontend): kubectl logs -f deployment/frontend -n $Namespace" -ForegroundColor White
Write-Host "  Port forward:        kubectl port-forward svc/frontend 8501:8501 -n $Namespace" -ForegroundColor White
Write-Host "  Shell into pod:      kubectl exec -it POD_NAME -n $Namespace -- /bin/bash" -ForegroundColor White
Write-Host ""
Write-Host "To initialize database, run:" -ForegroundColor Yellow
Write-Host "  kubectl exec -it deployment/backend -n $Namespace -- python init_db.py" -ForegroundColor White
