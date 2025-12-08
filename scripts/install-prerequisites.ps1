# Install Prerequisites for EKS Setup
# This script helps install required tools on Windows

Write-Host "Installing Prerequisites for EKS Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if (!$isAdmin) {
    Write-Host "WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "Some installations may require elevated privileges" -ForegroundColor Yellow
    Write-Host ""
}

# Function to check if command exists
function Test-Command {
    param($cmdname)
    return [bool](Get-Command -Name $cmdname -ErrorAction SilentlyContinue)
}

# Check AWS CLI
Write-Host "Checking AWS CLI..." -ForegroundColor Cyan
if (Test-Command aws) {
    $awsVersion = aws --version
    Write-Host "[OK] AWS CLI installed: $awsVersion" -ForegroundColor Green
} else {
    Write-Host "[MISSING] AWS CLI not found" -ForegroundColor Red
    Write-Host "Installing AWS CLI via winget..." -ForegroundColor Yellow
    
    if (Test-Command winget) {
        winget install -e --id Amazon.AWSCLI
    } else {
        Write-Host "Please install AWS CLI manually from: https://aws.amazon.com/cli/" -ForegroundColor Yellow
    }
}

# Check kubectl
Write-Host ""
Write-Host "Checking kubectl..." -ForegroundColor Cyan
if (Test-Command kubectl) {
    $kubectlVersion = kubectl version --client --short 2>$null
    Write-Host "[OK] kubectl installed: $kubectlVersion" -ForegroundColor Green
} else {
    Write-Host "[MISSING] kubectl not found" -ForegroundColor Red
    Write-Host "Installing kubectl..." -ForegroundColor Yellow
    
    # Download kubectl
    $kubectlUrl = "https://dl.k8s.io/release/v1.28.0/bin/windows/amd64/kubectl.exe"
    $kubectlPath = "$env:USERPROFILE\kubectl.exe"
    
    Write-Host "Downloading kubectl..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $kubectlUrl -OutFile $kubectlPath
    
    # Add to PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$env:USERPROFILE*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$env:USERPROFILE", "User")
        $env:Path = "$env:Path;$env:USERPROFILE"
    }
    
    Write-Host "[OK] kubectl installed to: $kubectlPath" -ForegroundColor Green
    Write-Host "     Added to PATH. Restart terminal if needed." -ForegroundColor Yellow
}

# Check eksctl
Write-Host ""
Write-Host "Checking eksctl..." -ForegroundColor Cyan
if (Test-Command eksctl) {
    $eksctlVersion = eksctl version
    Write-Host "[OK] eksctl installed: $eksctlVersion" -ForegroundColor Green
} else {
    Write-Host "[MISSING] eksctl not found" -ForegroundColor Red
    Write-Host "Installing eksctl..." -ForegroundColor Yellow
    
    # Download eksctl
    $eksctlUrl = "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_Windows_amd64.zip"
    $tempZip = "$env:TEMP\eksctl.zip"
    $eksctlPath = "$env:USERPROFILE\eksctl"
    
    Write-Host "Downloading eksctl..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $eksctlUrl -OutFile $tempZip
    
    # Extract
    Write-Host "Extracting..." -ForegroundColor Yellow
    Expand-Archive -Path $tempZip -DestinationPath $eksctlPath -Force
    
    # Add to PATH
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    if ($userPath -notlike "*$eksctlPath*") {
        [Environment]::SetEnvironmentVariable("Path", "$userPath;$eksctlPath", "User")
        $env:Path = "$env:Path;$eksctlPath"
    }
    
    # Cleanup
    Remove-Item $tempZip
    
    Write-Host "[OK] eksctl installed to: $eksctlPath" -ForegroundColor Green
    Write-Host "     Added to PATH. Restart terminal if needed." -ForegroundColor Yellow
}

# Check Docker
Write-Host ""
Write-Host "Checking Docker..." -ForegroundColor Cyan
if (Test-Command docker) {
    try {
        $dockerVersion = docker --version
        Write-Host "[OK] Docker installed: $dockerVersion" -ForegroundColor Green
        
        # Check if Docker is running
        docker info 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] Docker is running" -ForegroundColor Green
        } else {
            Write-Host "[WARNING] Docker is not running. Please start Docker Desktop." -ForegroundColor Yellow
        }
    } catch {
        Write-Host "[WARNING] Docker installed but not running" -ForegroundColor Yellow
    }
} else {
    Write-Host "[MISSING] Docker not found" -ForegroundColor Red
    Write-Host "Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "Installation Summary:" -ForegroundColor Cyan
Write-Host "====================" -ForegroundColor Cyan

$tools = @{
    "AWS CLI" = (Test-Command aws)
    "kubectl" = (Test-Command kubectl)
    "eksctl" = (Test-Command eksctl)
    "Docker" = (Test-Command docker)
}

foreach ($tool in $tools.GetEnumerator()) {
    if ($tool.Value) {
        Write-Host "  [OK] $($tool.Key)" -ForegroundColor Green
    } else {
        Write-Host "  [MISSING] $($tool.Key)" -ForegroundColor Red
    }
}

Write-Host ""
if ($tools.Values -contains $false) {
    Write-Host "WARNING: Some tools are missing. Please restart your terminal and run this script again." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "If installations failed, install manually:" -ForegroundColor Yellow
    Write-Host "  AWS CLI: https://aws.amazon.com/cli/" -ForegroundColor White
    Write-Host "  kubectl: https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/" -ForegroundColor White
    Write-Host "  eksctl:  https://eksctl.io/installation/" -ForegroundColor White
    Write-Host "  Docker:  https://www.docker.com/products/docker-desktop/" -ForegroundColor White
} else {
    Write-Host "SUCCESS: All prerequisites installed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Configure AWS: aws configure" -ForegroundColor White
    Write-Host "  2. Restart terminal (if new installs)" -ForegroundColor White
    Write-Host "  3. Run: .\setup-eks-cluster.ps1" -ForegroundColor White
}

Write-Host ""
Write-Host "TIP: You may need to restart your terminal for PATH changes to take effect" -ForegroundColor Cyan
