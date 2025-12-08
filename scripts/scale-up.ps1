# Scale Up EKS Cluster
# Run this script in the morning to restart the cluster

Write-Host "☀️ Starting EKS cluster..." -ForegroundColor Yellow
Write-Host ""

# Step 1: Scale up nodes
Write-Host "Step 1/5: Scaling up node group to 2 nodes..." -ForegroundColor Cyan
aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=1,maxSize=3,desiredSize=2 `
  --region us-east-1

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ Failed to scale up cluster" -ForegroundColor Red
    Write-Host "Check your AWS credentials and cluster name" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "⏳ Waiting for nodes to be ready (this takes ~5 minutes)..." -ForegroundColor Yellow
Write-Host "   You can press Ctrl+C and continue manually if needed" -ForegroundColor Gray
Write-Host ""

# Wait for nodes
Start-Sleep -Seconds 180

# Step 2: Check nodes
Write-Host "Step 2/5: Checking node status..." -ForegroundColor Cyan
kubectl get nodes
Write-Host ""

# Check if nodes are ready
$nodeCount = (kubectl get nodes --no-headers 2>$null | Measure-Object).Count
if ($nodeCount -eq 0) {
    Write-Host "⚠️  Nodes not ready yet. Wait 2 more minutes and run:" -ForegroundColor Yellow
    Write-Host "   kubectl get nodes" -ForegroundColor White
    Write-Host ""
}

# Step 3: Wait a bit more for system pods
Write-Host "Step 3/5: Waiting for system pods to initialize..." -ForegroundColor Cyan
Start-Sleep -Seconds 60

# Step 4: Restart deployments
Write-Host "Step 4/5: Restarting application deployments..." -ForegroundColor Cyan
kubectl rollout restart deployment/backend -n prompt2mesh 2>$null
kubectl rollout restart deployment/frontend -n prompt2mesh 2>$null
kubectl rollout restart deployment/postgres -n prompt2mesh 2>$null
Write-Host ""

Write-Host "⏳ Waiting for deployments to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 60

# Step 5: Check status
Write-Host "Step 5/5: Checking application status..." -ForegroundColor Cyan
Write-Host ""
kubectl get pods -n prompt2mesh
Write-Host ""

# Get URL
Write-Host "Getting application URL..." -ForegroundColor Cyan
$frontendUrl = kubectl get svc frontend -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>$null

if ($frontendUrl) {
    Write-Host ""
    Write-Host "✅ Cluster is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Application URL: http://${frontendUrl}:8501" -ForegroundColor White
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
    
    $openBrowser = Read-Host "Open in browser? (Y/n)"
    if ($openBrowser -ne 'n' -and $openBrowser -ne 'N') {
        Write-Host "Opening browser..." -ForegroundColor Yellow
        Start-Process "http://${frontendUrl}:8501"
    }
} else {
    Write-Host ""
    Write-Host "⚠️  LoadBalancer URL not ready yet." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Wait 2-3 minutes and run:" -ForegroundColor Cyan
    Write-Host "  kubectl get svc frontend -n prompt2mesh" -ForegroundColor White
    Write-Host ""
}

Write-Host ""
Write-Host "📋 Useful commands:" -ForegroundColor Cyan
Write-Host "   kubectl get nodes                  # Check node status" -ForegroundColor Gray
Write-Host "   kubectl get pods -n prompt2mesh    # Check pod status" -ForegroundColor Gray
Write-Host "   kubectl get svc -n prompt2mesh     # Check services" -ForegroundColor Gray
Write-Host ""
