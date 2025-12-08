# Cleanup EKS Resources
# This script removes all Prompt2Mesh resources from AWS

param(
    [string]$ClusterName = "prompt2mesh-cluster",
    [string]$Region = "us-east-1",
    [string]$Namespace = "prompt2mesh",
    [switch]$DeleteCluster = $false,
    [switch]$DeleteECR = $false,
    [switch]$Force = $false
)

Write-Host "🧹 Cleaning up Prompt2Mesh resources" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan
Write-Host ""

if (!$Force) {
    Write-Host "⚠️  WARNING: This will delete resources!" -ForegroundColor Red
    Write-Host "Resources to delete:" -ForegroundColor Yellow
    Write-Host "  - Kubernetes deployments in namespace: $Namespace" -ForegroundColor White
    if ($DeleteCluster) {
        Write-Host "  - EKS Cluster: $ClusterName" -ForegroundColor White
    }
    if ($DeleteECR) {
        Write-Host "  - ECR Repositories" -ForegroundColor White
    }
    Write-Host ""
    
    $confirm = Read-Host "Are you sure? (type 'yes' to confirm)"
    if ($confirm -ne "yes") {
        Write-Host "❌ Cleanup cancelled" -ForegroundColor Yellow
        exit 0
    }
}

# Delete Kubernetes resources
Write-Host ""
Write-Host "🗑️  Deleting Kubernetes resources..." -ForegroundColor Cyan

if (Get-Command kubectl -ErrorAction SilentlyContinue) {
    # Delete all user pods first
    Write-Host "  Deleting user Blender pods..." -ForegroundColor Yellow
    kubectl delete pods -l managed-by=prompt2mesh -n $Namespace --grace-period=0 --force 2>$null
    
    # Delete deployments
    Write-Host "  Deleting deployments..." -ForegroundColor Yellow
    kubectl delete deployment --all -n $Namespace 2>$null
    
    # Delete services
    Write-Host "  Deleting services..." -ForegroundColor Yellow
    kubectl delete svc --all -n $Namespace 2>$null
    
    # Delete PVCs
    Write-Host "  Deleting PVCs..." -ForegroundColor Yellow
    kubectl delete pvc --all -n $Namespace 2>$null
    
    # Delete secrets
    Write-Host "  Deleting secrets..." -ForegroundColor Yellow
    kubectl delete secret --all -n $Namespace 2>$null
    
    # Delete RBAC
    Write-Host "  Deleting RBAC resources..." -ForegroundColor Yellow
    kubectl delete -f .\k8s\rbac.yaml -n $Namespace 2>$null
    
    # Delete namespace
    Write-Host "  Deleting namespace..." -ForegroundColor Yellow
    kubectl delete namespace $Namespace 2>$null
    
    Write-Host "✅ Kubernetes resources deleted" -ForegroundColor Green
} else {
    Write-Host "⚠️  kubectl not found, skipping Kubernetes cleanup" -ForegroundColor Yellow
}

# Delete ECR repositories
if ($DeleteECR) {
    Write-Host ""
    Write-Host "🗑️  Deleting ECR repositories..." -ForegroundColor Cyan
    
    if (Test-Path ".\ecr-config.json") {
        $config = Get-Content ".\ecr-config.json" | ConvertFrom-Json
        
        foreach ($repoName in @("prompt2mesh/backend", "prompt2mesh/frontend", "prompt2mesh/blender-mcp")) {
            Write-Host "  Deleting: $repoName..." -ForegroundColor Yellow
            aws ecr delete-repository --region $Region --repository-name $repoName --force 2>$null
        }
        
        Write-Host "✅ ECR repositories deleted" -ForegroundColor Green
        
        # Delete config file
        Remove-Item ".\ecr-config.json" -ErrorAction SilentlyContinue
    } else {
        Write-Host "⚠️  ECR config not found" -ForegroundColor Yellow
    }
}

# Delete EKS cluster
if ($DeleteCluster) {
    Write-Host ""
    Write-Host "🗑️  Deleting EKS cluster..." -ForegroundColor Cyan
    Write-Host "   This will take 10-15 minutes..." -ForegroundColor Yellow
    
    if (Get-Command eksctl -ErrorAction SilentlyContinue) {
        eksctl delete cluster --region $Region --name $ClusterName --wait
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✅ EKS cluster deleted" -ForegroundColor Green
        } else {
            Write-Host "❌ Failed to delete cluster" -ForegroundColor Red
        }
        
        # Delete config file
        Remove-Item ".\eks-cluster-config.yaml" -ErrorAction SilentlyContinue
    } else {
        Write-Host "⚠️  eksctl not found, skipping cluster deletion" -ForegroundColor Yellow
        Write-Host "   Manual deletion required via AWS Console" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✅ Cleanup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "📝 Remaining manual cleanup (if needed):" -ForegroundColor Yellow
Write-Host "  - Check AWS Console for any remaining resources" -ForegroundColor White
Write-Host "  - Delete CloudWatch log groups" -ForegroundColor White
Write-Host "  - Delete any remaining EBS volumes" -ForegroundColor White
Write-Host "  - Delete VPC and related networking resources" -ForegroundColor White
