# Kubernetes Deployment Guide for Prompt2Mesh

This guide explains how to deploy Prompt2Mesh to AWS EKS using Kubernetes.

## Prerequisites

1. **Terraform deployed** - EKS cluster must be running
2. **kubectl installed** - https://kubernetes.io/docs/tasks/tools/
3. **AWS CLI configured** - `aws configure`
4. **Docker images pushed to ECR** - Completed in previous step

## Step 1: Configure kubectl

After Terraform creates your EKS cluster, configure kubectl:

```powershell
aws eks update-kubeconfig --region us-east-1 --name prompt2mesh-cluster
```

Verify connection:
```powershell
kubectl get nodes
```

You should see your EKS worker nodes.

## Step 2: Update Secrets

Before deploying, update the secrets file with your actual API keys:

```powershell
# Generate secure passwords
$postgresPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 16 | ForEach-Object {[char]$_})
$jwtSecret = [Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))

# Create secrets (replace YOUR_API_KEY with actual values)
kubectl create secret generic prompt2mesh-secrets `
  --from-literal=ANTHROPIC_API_KEY=YOUR_API_KEY `
  --from-literal=JWT_SECRET_KEY=$jwtSecret `
  --from-literal=POSTGRES_PASSWORD=$postgresPassword `
  --from-literal=DATABASE_URL="postgresql://postgres:$postgresPassword@postgres-service:5432/prompt2mesh_auth" `
  --from-literal=S3_BUCKET_NAME=prompt2mesh-user-files-785186658816 `
  --from-literal=S3_REGION=us-east-1 `
  --from-literal=LANGCHAIN_API_KEY=YOUR_LANGCHAIN_KEY `
  --from-literal=LANGSMITH_API_KEY=YOUR_LANGSMITH_KEY `
  --namespace=prompt2mesh `
  --dry-run=client -o yaml | kubectl apply -f -
```

## Step 3: Deploy Base Infrastructure

Deploy in order:

```powershell
cd C:\Prompt2Mesh\k8s\base

# 1. Create namespace
kubectl apply -f namespace.yaml

# 2. Create ConfigMap
kubectl apply -f configmap.yaml

# 3. Create Secrets (if not created in Step 2)
kubectl apply -f secrets.yaml

# 4. Deploy PostgreSQL
kubectl apply -f postgres-statefulset.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s

# 5. Initialize Database
kubectl apply -f db-init-job.yaml

# Wait for DB init to complete
kubectl wait --for=condition=complete job/db-init -n prompt2mesh --timeout=300s

# 6. Deploy Backend
kubectl apply -f backend-deployment.yaml

# 7. Deploy Streamlit
kubectl apply -f streamlit-deployment.yaml

# 8. Deploy Blender
kubectl apply -f blender-deployment.yaml
```

## Step 4: Verify Deployments

Check all pods are running:

```powershell
kubectl get pods -n prompt2mesh
```

Expected output:
```
NAME                        READY   STATUS      RESTARTS   AGE
postgres-0                  1/1     Running     0          5m
db-init-xxxxx               0/1     Completed   0          4m
backend-xxxxx-xxxxx         1/1     Running     0          3m
backend-xxxxx-xxxxx         1/1     Running     0          3m
streamlit-xxxxx-xxxxx       1/1     Running     0          2m
streamlit-xxxxx-xxxxx       1/1     Running     0          2m
blender-xxxxx-xxxxx         1/1     Running     0          1m
blender-xxxxx-xxxxx         1/1     Running     0          1m
```

## Step 5: Get Service URLs

Get LoadBalancer URLs:

```powershell
kubectl get services -n prompt2mesh
```

Look for `EXTERNAL-IP` for:
- `streamlit-service` - Your Streamlit UI
- `blender-service` - Your Blender Web UI

Example:
```
NAME                TYPE           EXTERNAL-IP                        PORT(S)
streamlit-service   LoadBalancer   abc123.us-east-1.elb.amazonaws.com 80:30001/TCP
blender-service     LoadBalancer   def456.us-east-1.elb.amazonaws.com 80:30002/TCP
```

Access your application:
- Streamlit: http://abc123.us-east-1.elb.amazonaws.com
- Blender: http://def456.us-east-1.elb.amazonaws.com

## Step 6: Monitor Deployment

View logs:
```powershell
# Backend logs
kubectl logs -f deployment/backend -n prompt2mesh

# Streamlit logs
kubectl logs -f deployment/streamlit -n prompt2mesh

# Blender logs
kubectl logs -f deployment/blender -n prompt2mesh

# PostgreSQL logs
kubectl logs -f statefulset/postgres -n prompt2mesh
```

## Troubleshooting

### Pods Not Starting

```powershell
# Describe pod to see events
kubectl describe pod <pod-name> -n prompt2mesh

# Check if image pull succeeded
kubectl get events -n prompt2mesh --sort-by='.lastTimestamp'
```

### Database Connection Issues

```powershell
# Check PostgreSQL is running
kubectl exec -it postgres-0 -n prompt2mesh -- pg_isready -U postgres

# Test database connection
kubectl exec -it postgres-0 -n prompt2mesh -- psql -U postgres -d prompt2mesh_auth -c "\dt"
```

### LoadBalancer Not Getting External IP

```powershell
# Check service status
kubectl describe service streamlit-service -n prompt2mesh

# If stuck in <pending>, check AWS console for ELB creation errors
```

### ImagePullBackOff Error

```powershell
# Verify ECR access
aws ecr describe-repositories --region us-east-1

# Check EKS node IAM role has ECR permissions
# Should have: AmazonEC2ContainerRegistryReadOnly policy
```

## Updating Deployments

When you push new images to ECR:

```powershell
# Restart deployments to pull new images
kubectl rollout restart deployment/backend -n prompt2mesh
kubectl rollout restart deployment/streamlit -n prompt2mesh
kubectl rollout restart deployment/blender -n prompt2mesh

# Watch rollout status
kubectl rollout status deployment/backend -n prompt2mesh
```

## Scaling

Scale deployments:

```powershell
# Scale backend
kubectl scale deployment/backend --replicas=3 -n prompt2mesh

# Scale Streamlit
kubectl scale deployment/streamlit --replicas=3 -n prompt2mesh
```

## Cleanup

To delete everything:

```powershell
kubectl delete namespace prompt2mesh
```

## Cost Optimization

After your presentation (Dec 12), you can:

1. **Scale down to save costs**:
   ```powershell
   kubectl scale deployment/backend --replicas=0 -n prompt2mesh
   kubectl scale deployment/streamlit --replicas=0 -n prompt2mesh
   kubectl scale deployment/blender --replicas=0 -n prompt2mesh
   ```

2. **Delete cluster** (via Terraform):
   ```powershell
   cd C:\Prompt2Mesh\infrastructure\terraform
   terraform destroy
   ```

## Next Steps

- Set up per-user namespaces (see `k8s/per-user/` directory)
- Configure domain and HTTPS
- Set up monitoring and alerts
- Implement backup strategy
