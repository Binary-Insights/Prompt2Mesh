# Scale Down EKS Cluster
# Run this script at night to save costs

Write-Host "🌙 Scaling down EKS cluster..." -ForegroundColor Yellow
Write-Host ""

# Scale down node group to 0
Write-Host "Scaling node group to 0 nodes..." -ForegroundColor Cyan
aws eks update-nodegroup-config `
  --cluster-name prompt2mesh-cluster `
  --nodegroup-name prompt2mesh-nodegroup `
  --scaling-config minSize=0,maxSize=3,desiredSize=0 `
  --region us-east-1

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Cluster is scaling down. This will take ~3-5 minutes." -ForegroundColor Green
    Write-Host ""
    Write-Host "To verify shutdown:" -ForegroundColor Cyan
    Write-Host "  kubectl get nodes" -ForegroundColor White
    Write-Host ""
    Write-Host "Expected result: No resources found" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "❌ Failed to scale down cluster" -ForegroundColor Red
    Write-Host "Check your AWS credentials and cluster name" -ForegroundColor Yellow
}
