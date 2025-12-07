# AWS ECR Setup Guide for Prompt2Mesh

This guide explains how to set up AWS Elastic Container Registry (ECR) repositories and push your Docker images.

## Prerequisites

1. **AWS CLI installed and configured**
   - Install: https://aws.amazon.com/cli/
   - Configure: `aws configure`
   - You need:
     - AWS Access Key ID
     - AWS Secret Access Key
     - Default region (e.g., `us-east-1`)

2. **Docker installed and running**
   - Your Docker images should be built locally

3. **AWS Account with ECR permissions**
   - You need permissions to create ECR repositories and push images

## Step 1: Configure AWS CLI

If you haven't configured AWS CLI yet:

```powershell
aws configure
```

Enter your:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (e.g., `us-east-1`)
- Output format (e.g., `json`)

## Step 2: Get Your AWS Account ID

```powershell
aws sts get-caller-identity --query Account --output text
```

Save this Account ID - you'll need it for the next steps.

## Step 3: Create ECR Repositories

Run the ECR setup script:

**PowerShell (Windows):**
```powershell
cd C:\Prompt2Mesh\infrastructure
.\ecr-setup.ps1 -Region us-east-1 -AccountId YOUR_ACCOUNT_ID
```

**Bash (Linux/Mac/WSL):**
```bash
cd /mnt/c/Prompt2Mesh/infrastructure
chmod +x ecr-setup.sh
./ecr-setup.sh us-east-1 YOUR_ACCOUNT_ID
```

This creates 4 ECR repositories:
- `prompt2mesh/backend`
- `prompt2mesh/streamlit`
- `prompt2mesh/blender`
- `prompt2mesh/db-init`

## Step 4: Build Docker Images Locally

Make sure your Docker images are built:

```powershell
cd C:\Prompt2Mesh\docker
docker-compose build
```

Verify images exist:
```powershell
docker images | Select-String "docker-backend|docker-streamlit|docker-db-init"
```

## Step 5: Push Images to ECR

Run the push script:

**PowerShell (Windows):**
```powershell
cd C:\Prompt2Mesh\scripts
.\push-to-ecr.ps1 -Region us-east-1 -AccountId YOUR_ACCOUNT_ID
```

**Bash (Linux/Mac/WSL):**
```bash
cd /mnt/c/Prompt2Mesh/scripts
chmod +x push-to-ecr.sh
./push-to-ecr.sh us-east-1 YOUR_ACCOUNT_ID
```

## Step 6: Verify Images in ECR

Check that images were pushed successfully:

```powershell
aws ecr describe-images --repository-name prompt2mesh/backend --region us-east-1
aws ecr describe-images --repository-name prompt2mesh/streamlit --region us-east-1
aws ecr describe-images --repository-name prompt2mesh/db-init --region us-east-1
aws ecr describe-images --repository-name prompt2mesh/blender --region us-east-1
```

Or view in AWS Console:
- Go to: https://console.aws.amazon.com/ecr/
- Select your region
- You should see all 4 repositories with images

## Image URIs

After pushing, your images will be available at:
```
YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/prompt2mesh/backend:latest
YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/prompt2mesh/streamlit:latest
YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/prompt2mesh/db-init:latest
YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/prompt2mesh/blender:latest
```

These URIs will be used in your Kubernetes manifests for EKS deployment.

## Updating Images

When you update your code and want to push new images:

1. Rebuild images:
   ```powershell
   cd C:\Prompt2Mesh\docker
   docker-compose build --no-cache
   ```

2. Push to ECR again:
   ```powershell
   cd C:\Prompt2Mesh\scripts
   .\push-to-ecr.ps1 -Region us-east-1 -AccountId YOUR_ACCOUNT_ID
   ```

## Troubleshooting

### Authentication Error
If you get authentication errors:
```powershell
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com
```

### Repository Already Exists
This is normal - the script handles existing repositories gracefully.

### Image Not Found
Make sure you've built the images locally first:
```powershell
docker-compose build
```

### Access Denied
Ensure your AWS user has the following IAM permissions:
- `ecr:CreateRepository`
- `ecr:GetAuthorizationToken`
- `ecr:BatchCheckLayerAvailability`
- `ecr:PutImage`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`

## Cost Considerations

ECR pricing (as of 2024):
- Storage: $0.10 per GB/month
- Data transfer: $0.09 per GB (outbound to internet)
- Data transfer within AWS region: Free

For your 4 images (~2-3 GB total):
- Storage: ~$0.30/month
- Transfer to EKS (same region): Free

## Next Steps

After pushing images to ECR, you can:
1. Create Kubernetes manifests that reference these ECR image URIs
2. Deploy to EKS cluster
3. Set up CI/CD to automatically push new images on code changes
