# Terraform Deployment Guide for Prompt2Mesh

This guide explains how to deploy the AWS infrastructure for Prompt2Mesh using Terraform.

## Prerequisites

1. **Terraform installed** - https://www.terraform.io/downloads
2. **AWS CLI configured** - `aws configure`
3. **ECR images pushed** - Completed in previous step

## Step 1: Initialize Terraform

```powershell
cd C:\Prompt2Mesh\infrastructure\terraform
terraform init
```

This downloads required providers (AWS, Kubernetes).

## Step 2: Review Plan

See what Terraform will create:

```powershell
terraform plan
```

Review the output carefully. You should see:
- EKS cluster
- EKS node group (2 t3.medium instances)
- IAM roles and policies
- Security groups
- S3 bucket
- Using default VPC and subnets

## Step 3: Deploy Infrastructure

```powershell
terraform apply
```

Type `yes` when prompted.

**This will take 15-20 minutes** as EKS cluster creation is slow.

## Step 4: Save Outputs

After deployment completes, save important outputs:

```powershell
# Get all outputs
terraform output

# Configure kubectl
terraform output -raw configure_kubectl | Invoke-Expression

# Or manually:
aws eks update-kubeconfig --region us-east-1 --name prompt2mesh-cluster
```

## Step 5: Verify Infrastructure

```powershell
# Check EKS cluster
aws eks describe-cluster --name prompt2mesh-cluster --region us-east-1

# Check S3 bucket
aws s3 ls | Select-String prompt2mesh

# Verify kubectl access
kubectl get nodes
```

You should see 2 nodes in "Ready" state.

## Important Outputs

```powershell
# EKS cluster name
terraform output eks_cluster_name

# S3 bucket name
terraform output s3_bucket_name

# ECR registry URL
terraform output ecr_registry_url

# Configure kubectl command
terraform output configure_kubectl
```

## Cost Estimate

Based on your configuration:
- **EKS cluster**: $0.10/hour ($2.40/day)
- **2x t3.medium nodes**: $0.0416/hour each ($2.00/day total)
- **EBS storage (60GB)**: $6/month
- **S3 storage**: ~$0.30/month
- **LoadBalancers (2)**: $0.025/hour each ($1.20/day total)

**Total: ~$5.60/day or ~$34 for 6 days (until Dec 12)**

## Updating Infrastructure

If you need to change configuration:

1. Edit `variables.tf` or other `.tf` files
2. Run:
   ```powershell
   terraform plan
   terraform apply
   ```

## Troubleshooting

### Error: Insufficient capacity

If node creation fails with capacity errors, try different instance types:

Edit `variables.tf`:
```hcl
variable "eks_node_instance_types" {
  default     = ["t3.medium", "t3a.medium", "t2.medium"]
}
```

Then run `terraform apply` again.

### Error: VPC quota exceeded

If using default VPC causes issues, you may need to create a custom VPC. Contact me if this happens.

### Error: Cannot authenticate to cluster

```powershell
# Re-configure kubectl
aws eks update-kubeconfig --region us-east-1 --name prompt2mesh-cluster

# Verify
kubectl get nodes
```

## Cleanup (After Presentation)

To delete all infrastructure and stop charges:

```powershell
# First, delete Kubernetes resources
kubectl delete namespace prompt2mesh

# Wait a few minutes for LoadBalancers to be deleted

# Then destroy Terraform infrastructure
terraform destroy
```

Type `yes` when prompted.

**Important**: Make sure to delete everything to avoid ongoing charges!

## State Management (Optional)

For team collaboration, store Terraform state in S3:

1. Create state bucket:
   ```powershell
   aws s3 mb s3://prompt2mesh-terraform-state --region us-east-1
   ```

2. Uncomment backend configuration in `main.tf`

3. Initialize backend:
   ```powershell
   terraform init -migrate-state
   ```

## Next Steps

After Terraform completes:
1. Follow Kubernetes deployment guide (`k8s/DEPLOYMENT_GUIDE.md`)
2. Deploy your applications
3. Test with 2 users + admin

## Support

If you encounter issues:
1. Check AWS Console for detailed error messages
2. Review Terraform logs
3. Verify IAM permissions
4. Check AWS service quotas
