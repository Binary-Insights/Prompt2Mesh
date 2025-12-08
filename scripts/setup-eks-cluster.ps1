# Setup EKS Cluster for Prompt2Mesh
# This script creates a new EKS cluster with all required configurations

param(
    [string]$ClusterName = "prompt2mesh-cluster",
    [string]$Region = "us-east-1",
    [string]$NodeType = "t3.large",
    [int]$MinNodes = 2,
    [int]$MaxNodes = 5,
    [string]$K8sVersion = "1.31"
)

Write-Host "Setting up EKS cluster for Prompt2Mesh" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "Cluster Name: $ClusterName" -ForegroundColor Yellow
Write-Host "Region: $Region" -ForegroundColor Yellow
Write-Host "Node Type: $NodeType" -ForegroundColor Yellow
Write-Host "Nodes: $MinNodes-$MaxNodes" -ForegroundColor Yellow
Write-Host "Kubernetes Version: $K8sVersion" -ForegroundColor Yellow
Write-Host ""

# Check prerequisites
Write-Host "Checking prerequisites..." -ForegroundColor Cyan

$commands = @("aws", "eksctl", "kubectl")
$missing = @()

foreach ($cmd in $commands) {
    if (!(Get-Command $cmd -ErrorAction SilentlyContinue)) {
        $missing += $cmd
    }
}

if ($missing.Count -gt 0) {
    Write-Host "[ERROR] Missing required tools: $($missing -join ', ')" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install:" -ForegroundColor Yellow
    Write-Host "  AWS CLI: https://aws.amazon.com/cli/" -ForegroundColor White
    Write-Host "  eksctl: https://eksctl.io/installation/" -ForegroundColor White
    Write-Host "  kubectl: https://kubernetes.io/docs/tasks/tools/" -ForegroundColor White
    exit 1
}

Write-Host "[OK] All prerequisites installed" -ForegroundColor Green

# Check AWS credentials
Write-Host ""
Write-Host "Checking AWS credentials..." -ForegroundColor Cyan
try {
    $identity = aws sts get-caller-identity --output json | ConvertFrom-Json
    Write-Host "[OK] Authenticated as: $($identity.Arn)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] AWS credentials not configured" -ForegroundColor Red
    Write-Host "Run: aws configure" -ForegroundColor Yellow
    exit 1
}

# Create cluster
Write-Host ""
Write-Host "Creating EKS cluster (this will take 15-20 minutes)..." -ForegroundColor Cyan

$clusterConfig = @"
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: $ClusterName
  region: $Region
  version: "$K8sVersion"

# Enable IAM OIDC provider for service accounts
iam:
  withOIDC: true

# Node groups
managedNodeGroups:
  - name: prompt2mesh-nodes
    instanceType: $NodeType
    minSize: $MinNodes
    maxSize: $MaxNodes
    desiredCapacity: $MinNodes
    volumeSize: 50
    volumeType: gp3
    privateNetworking: false
    labels:
      role: worker
      environment: production
    tags:
      Project: Prompt2Mesh
      ManagedBy: eksctl
    iam:
      withAddonPolicies:
        imageBuilder: true
        autoScaler: true
        externalDNS: true
        certManager: true
        appMesh: false
        ebs: true
        fsx: false
        efs: false
        albIngress: true
        xRay: false
        cloudWatch: true

# Add-ons
addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest
    attachPolicyARNs:
      - arn:aws:iam::aws:policy/service-role/AmazonEBSCSIDriverPolicy

# CloudWatch logging
cloudWatch:
  clusterLogging:
    enableTypes: ["api", "audit", "authenticator", "controllerManager", "scheduler"]
"@

$configPath = ".\eks-cluster-config.yaml"
$clusterConfig | Out-File -FilePath $configPath -Encoding UTF8

Write-Host "Cluster configuration saved to: $configPath" -ForegroundColor Yellow

# Create cluster
eksctl create cluster -f $configPath

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to create EKS cluster" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] EKS cluster created successfully" -ForegroundColor Green

# Update kubeconfig
Write-Host ""
Write-Host "Updating kubeconfig..." -ForegroundColor Cyan
aws eks update-kubeconfig --region $Region --name $ClusterName

if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to update kubeconfig" -ForegroundColor Red
    exit 1
}

Write-Host "[OK] kubeconfig updated" -ForegroundColor Green

# Verify cluster
Write-Host ""
Write-Host "Verifying cluster..." -ForegroundColor Cyan
kubectl cluster-info
kubectl get nodes

Write-Host ""
Write-Host "EKS cluster setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Run: .\setup-ecr.ps1" -ForegroundColor White
Write-Host "  2. Run: .\build-and-push-images.ps1" -ForegroundColor White
Write-Host "  3. Run: .\deploy-to-eks.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Cluster details:" -ForegroundColor Yellow
Write-Host "  Name: $ClusterName" -ForegroundColor White
Write-Host "  Region: $Region" -ForegroundColor White
$endpoint = kubectl config view --minify -o jsonpath="{.clusters[0].cluster.server}"
Write-Host "  Endpoint: $endpoint" -ForegroundColor White
