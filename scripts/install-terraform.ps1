# Install Terraform on Windows using Chocolatey or direct download
# This script will install Terraform if not already installed

Write-Host "Checking if Terraform is installed..." -ForegroundColor Yellow

# Check if Terraform is already installed
$terraformInstalled = Get-Command terraform -ErrorAction SilentlyContinue

if ($terraformInstalled) {
    Write-Host "Terraform is already installed" -ForegroundColor Green
    terraform version
    exit 0
}

Write-Host "Terraform not found. Installing..." -ForegroundColor Yellow

# Check if Chocolatey is installed
$chocoInstalled = Get-Command choco -ErrorAction SilentlyContinue

if ($chocoInstalled) {
    Write-Host "Installing Terraform using Chocolatey..." -ForegroundColor Cyan
    choco install terraform -y
    
    # Refresh environment
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
    $userPath = [System.Environment]::GetEnvironmentVariable("Path","User")
    $env:Path = "$machinePath;$userPath"
    
    Write-Host "Terraform installed successfully via Chocolatey" -ForegroundColor Green
    terraform version
}
else {
    Write-Host "Chocolatey not found. Installing Terraform manually..." -ForegroundColor Cyan
    
    # Download and install Terraform manually
    $terraformVersion = "1.6.6"
    $downloadUrl = "https://releases.hashicorp.com/terraform/$terraformVersion/terraform_${terraformVersion}_windows_amd64.zip"
    $downloadPath = "$env:TEMP\terraform.zip"
    $installPath = "$env:LOCALAPPDATA\Terraform"
    
    Write-Host "Downloading Terraform $terraformVersion..." -ForegroundColor Cyan
    
    try {
        # Download Terraform
        Invoke-WebRequest -Uri $downloadUrl -OutFile $downloadPath -UseBasicParsing
        
        # Create install directory
        if (-not (Test-Path $installPath)) {
            New-Item -ItemType Directory -Path $installPath -Force | Out-Null
        }
        
        # Extract zip
        Write-Host "Extracting Terraform..." -ForegroundColor Cyan
        Expand-Archive -Path $downloadPath -DestinationPath $installPath -Force
        
        # Add to PATH
        Write-Host "Adding Terraform to PATH..." -ForegroundColor Cyan
        $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentPath -notlike "*$installPath*") {
            [Environment]::SetEnvironmentVariable(
                "Path",
                "$currentPath;$installPath",
                "User"
            )
        }
        
        # Update current session PATH
        $env:Path += ";$installPath"
        
        # Clean up
        Remove-Item $downloadPath -Force
        
        Write-Host "Terraform installed successfully to $installPath" -ForegroundColor Green
        Write-Host ""
        Write-Host "Please close and reopen your PowerShell window, then run:" -ForegroundColor Yellow
        Write-Host "  terraform version" -ForegroundColor Cyan
        Write-Host ""
    }
    catch {
        Write-Host "Error installing Terraform: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please install Terraform manually:" -ForegroundColor Yellow
        Write-Host "1. Download from: https://www.terraform.io/downloads" -ForegroundColor Cyan
        Write-Host "2. Extract to a folder like C:\Terraform" -ForegroundColor Cyan
        Write-Host "3. Add that folder to your PATH environment variable" -ForegroundColor Cyan
        exit 1
    }
}
