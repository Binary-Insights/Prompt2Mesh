# Prompt2Mesh EKS Setup Guide

Complete guide for deploying Prompt2Mesh to Amazon EKS from scratch.

## Prerequisites

### Required Tools

1. **AWS CLI** - Install from https://aws.amazon.com/cli/
   ```powershell
   winget install Amazon.AWSCLI
   ```

2. **eksctl** - EKS cluster management tool
   ```powershell
   choco install eksctl
   # or download from https://eksctl.io/installation/
   ```

3. **kubectl** - Kubernetes CLI
   ```powershell
   choco install kubernetes-cli
   # or download from https://kubernetes.io/docs/tasks/tools/
   ```

4. **Docker Desktop** - For building images
   - Download from https://www.docker.com/products/docker-desktop/

### AWS Configuration

1. **Configure AWS credentials:**
   ```powershell
   aws configure
   ```
   Enter:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (e.g., us-east-1)
   - Default output format (json)

2. **Verify authentication:**
   ```powershell
   aws sts get-caller-identity
   ```

## Step-by-Step Setup

### Step 1: Create EKS Cluster

This creates a new EKS cluster with auto-scaling node group and EBS CSI driver.

```powershell
.\setup-eks-cluster.ps1
```

**Parameters (optional):**
```powershell
.\setup-eks-cluster.ps1 `
    -ClusterName "prompt2mesh-cluster" `
    -Region "us-east-1" `
    -NodeType "t3.medium" `
    -MinNodes 2 `
    -MaxNodes 5 `
    -K8sVersion "1.28"
```

**What it does:**
- Creates EKS cluster with managed node group
- Installs AWS EBS CSI driver for persistent volumes
- Configures IAM roles and OIDC provider
- Updates your kubeconfig
- Enables CloudWatch logging

**Duration:** 15-20 minutes

### Step 2: Create ECR Repositories

This creates private Docker registries for your images.

```powershell
.\setup-ecr.ps1
```

**Parameters (optional):**
```powershell
.\setup-ecr.ps1 -Region "us-east-1" -Prefix "prompt2mesh"
```

**What it does:**
- Creates three ECR repositories:
  - `prompt2mesh/backend`
  - `prompt2mesh/frontend`
  - `prompt2mesh/blender-mcp`
- Enables image scanning and encryption
- Sets lifecycle policy (keep last 10 images)
- Saves configuration to `ecr-config.json`

### Step 3: Build and Push Images

This builds Docker images locally and pushes to ECR.

```powershell
.\build-and-push-images.ps1
```

**Parameters (optional):**
```powershell
.\build-and-push-images.ps1 -Tag "v1.0"
```

**What it does:**
- Authenticates Docker with ECR
- Builds three images:
  - Backend (FastAPI + Kubernetes client)
  - Frontend (Streamlit UI)
  - Blender MCP (Blender with MCP server)
- Pushes all images to ECR

**Duration:** 10-15 minutes (depending on internet speed)

### Step 4: Update Kubernetes Manifests

This updates YAML files with ECR image URIs.

```powershell
.\update-k8s-manifests.ps1
```

**What it does:**
- Updates `k8s/backend-deployment.yaml`
- Updates `k8s/frontend-deployment.yaml`
- Updates `src/backend/k8s_user_session_manager.py`
- Replaces placeholder images with actual ECR URIs

### Step 5: Deploy to EKS

This deploys all resources to your cluster.

```powershell
.\deploy-to-eks.ps1
```

**What it does:**
- Creates namespace `prompt2mesh`
- Applies StorageClass for persistent volumes
- Creates secrets (prompts for sensitive data)
- Deploys PostgreSQL database
- Deploys backend API
- Deploys frontend UI
- Waits for all pods to be ready

**Required inputs:**
- Database password
- JWT secret
- Anthropic API key

**Duration:** 5-10 minutes

### Step 6: Initialize Database

Once deployed, initialize the database schema:

```powershell
kubectl exec -it deployment/backend -n prompt2mesh -- python init_db.py
```

### Step 7: Access Your Application

Get the frontend URL:

```powershell
kubectl get svc frontend -n prompt2mesh
```

The `EXTERNAL-IP` column shows your LoadBalancer URL. Access at:
```
http://<EXTERNAL-IP>:8501
```

**Note:** LoadBalancer provisioning may take 5-10 minutes.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          AWS EKS Cluster                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐               │
│  │  Frontend  │  │   Backend  │  │  PostgreSQL │               │
│  │ (Streamlit)│  │  (FastAPI) │  │     (DB)    │               │
│  │    Pod     │  │     Pod    │  │     Pod     │               │
│  └────────────┘  └────────────┘  └─────────────┘               │
│        │               │                 │                      │
│        │               │                 │                      │
│  ┌────────────┐  ┌─────────────────────────────────┐           │
│  │ LoadBalancer│ │  Per-User Blender Pods          │           │
│  │  Service   │  │  (Created dynamically on login) │           │
│  └────────────┘  │                                 │           │
│        │         │  ┌──────────┐  ┌──────────┐    │           │
│    Internet      │  │ Blender  │  │ Blender  │    │           │
│                  │  │  User1   │  │  User2   │    │           │
│                  │  │   Pod    │  │   Pod    │    │           │
│                  │  └──────────┘  └──────────┘    │           │
│                  └─────────────────────────────────┘           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ Persistent Volumes (AWS EBS via CSI Driver)              │  │
│  │ - Database storage                                       │  │
│  │ - Per-user Blender data                                  │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Resource Specifications

### Node Group
- Instance Type: t3.medium (2 vCPU, 4 GB RAM)
- Min Nodes: 2
- Max Nodes: 5
- Auto-scaling enabled

### Pods

**Backend:**
- CPU: 500m - 2 cores
- Memory: 1Gi - 4Gi
- Replicas: 1

**Frontend:**
- CPU: 250m - 1 core
- Memory: 512Mi - 2Gi
- Replicas: 1

**PostgreSQL:**
- CPU: 250m - 1 core
- Memory: 512Mi - 2Gi
- Storage: 10Gi (PVC)

**Blender (per user):**
- CPU: 500m - 2 cores
- Memory: 1Gi - 4Gi
- Storage: 5Gi (PVC per user)

## Monitoring and Debugging

### View all resources
```powershell
kubectl get all -n prompt2mesh
```

### Check pod status
```powershell
kubectl get pods -n prompt2mesh
kubectl describe pod <pod-name> -n prompt2mesh
```

### View logs
```powershell
# Backend logs
kubectl logs -f deployment/backend -n prompt2mesh

# Frontend logs
kubectl logs -f deployment/frontend -n prompt2mesh

# User Blender pod logs
kubectl logs -f <blender-pod-name> -n prompt2mesh
```

### Port forwarding (local testing)
```powershell
# Access frontend locally
kubectl port-forward svc/frontend 8501:8501 -n prompt2mesh

# Access backend locally
kubectl port-forward svc/backend 8000:8000 -n prompt2mesh
```

### Shell into pod
```powershell
kubectl exec -it deployment/backend -n prompt2mesh -- /bin/bash
```

### View events
```powershell
kubectl get events -n prompt2mesh --sort-by='.lastTimestamp'
```

## Scaling

### Scale deployments manually
```powershell
kubectl scale deployment backend --replicas=2 -n prompt2mesh
kubectl scale deployment frontend --replicas=2 -n prompt2mesh
```

### Scale node group
```powershell
eksctl scale nodegroup --cluster=prompt2mesh-cluster --region=us-east-1 --name=prompt2mesh-nodes --nodes=3
```

## Cost Optimization

### Estimated Monthly Costs (us-east-1)

**EKS Control Plane:** $73/month  
**EC2 Nodes (2x t3.medium):** ~$60/month  
**EBS Volumes:** ~$5-10/month  
**LoadBalancer:** ~$16/month  
**Data Transfer:** Variable  

**Total:** ~$150-160/month for base infrastructure

### Cost Saving Tips

1. **Use Spot Instances** for node group (50-70% savings)
2. **Stop cluster** when not in use
3. **Use gp3** instead of gp2 for EBS (20% cheaper)
4. **Enable cluster autoscaler** to scale down when idle
5. **Set up budget alerts** in AWS Billing

## Cleanup

### Delete Kubernetes resources only
```powershell
.\cleanup-eks.ps1
```

### Delete everything including cluster and ECR
```powershell
.\cleanup-eks.ps1 -DeleteCluster -DeleteECR -Force
```

### Manual cleanup checklist
- [ ] Delete EKS cluster
- [ ] Delete ECR repositories
- [ ] Delete EBS volumes
- [ ] Delete VPC and networking
- [ ] Delete CloudWatch log groups
- [ ] Delete IAM roles (if not used elsewhere)

## Troubleshooting

### Pod stuck in Pending
```powershell
kubectl describe pod <pod-name> -n prompt2mesh
```
Common causes:
- Insufficient resources
- PVC not bound
- Image pull errors

### Image pull errors
```powershell
# Check ECR authentication
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Verify image exists
aws ecr describe-images --repository-name prompt2mesh/backend --region us-east-1
```

### LoadBalancer not getting external IP
```powershell
kubectl describe svc frontend -n prompt2mesh
```
Wait 5-10 minutes for AWS to provision the LoadBalancer.

### Backend can't create user pods
Check RBAC permissions:
```powershell
kubectl get sa backend-sa -n prompt2mesh
kubectl get role pod-manager -n prompt2mesh
kubectl get rolebinding backend-pod-manager -n prompt2mesh
```

### Database connection errors
```powershell
# Check PostgreSQL pod
kubectl get pod -l app=postgres -n prompt2mesh

# Check service
kubectl get svc postgres -n prompt2mesh

# Test connection from backend
kubectl exec -it deployment/backend -n prompt2mesh -- psql -h postgres -U prompt2mesh_user -d prompt2mesh_db
```

## Security Best Practices

1. **Use AWS Secrets Manager** instead of Kubernetes secrets for production
2. **Enable Pod Security Standards**
3. **Use Network Policies** to restrict pod-to-pod communication
4. **Enable AWS GuardDuty** for threat detection
5. **Regular security updates** for base images
6. **Use IAM roles** for service accounts (IRSA)
7. **Enable audit logging**
8. **Restrict API access** with security groups

## Maintenance

### Update cluster version
```powershell
eksctl upgrade cluster --name=prompt2mesh-cluster --region=us-east-1 --version=1.29 --approve
```

### Update deployments
```powershell
# Build new images with new tag
.\build-and-push-images.ps1 -Tag "v1.1"

# Update manifests
.\update-k8s-manifests.ps1 -Tag "v1.1"

# Rolling update
kubectl apply -f .\k8s\backend-deployment.yaml -n prompt2mesh
kubectl apply -f .\k8s\frontend-deployment.yaml -n prompt2mesh
```

### Backup database
```powershell
kubectl exec deployment/postgres -n prompt2mesh -- pg_dump -U prompt2mesh_user prompt2mesh_db > backup.sql
```

## Next Steps

1. **Set up Ingress** for proper domain routing
2. **Configure TLS/SSL** certificates
3. **Set up monitoring** with Prometheus/Grafana
4. **Configure autoscaling** with HPA
5. **Implement CI/CD** pipeline
6. **Set up disaster recovery**

## Support

For issues or questions:
1. Check pod logs: `kubectl logs -f <pod-name> -n prompt2mesh`
2. Check events: `kubectl get events -n prompt2mesh`
3. Review AWS CloudWatch logs
4. Check project documentation: `README.md`
