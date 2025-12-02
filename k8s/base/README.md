# Kubernetes Deployment Files

This directory contains all Kubernetes manifests and deployment scripts for EKS.

## Directory Structure

```
k8s/
├── base/                           # Shared base components
│   ├── namespace.yaml              # Namespace definition
│   ├── configmap.yaml              # Configuration
│   ├── secrets.yaml                # Secrets (use AWS Secrets Manager in prod)
│   ├── postgres-pvc.yaml           # PostgreSQL persistent volume
│   ├── postgres-deployment.yaml    # PostgreSQL deployment & service
│   ├── backend-deployment.yaml     # Backend API deployment & service
│   ├── streamlit-deployment.yaml   # Frontend UI deployment & service
│   ├── blender-deployment.yaml     # Shared Blender deployment & service
│   ├── db-init-job.yaml            # Database initialization job
│   └── ingress.yaml                # Main ingress (ALB)
├── per-user/                       # Per-user instance templates
│   └── user-instance-template.yaml # Template for creating user instances
├── user_instance_manager.py        # Python script to manage user instances
├── deploy.sh                       # Bash deployment script
├── deploy.ps1                      # PowerShell deployment script
└── README.md                       # This file
```

## Quick Start

### 1. Prerequisites

- AWS EKS cluster running
- `kubectl` configured to access your cluster
- AWS Load Balancer Controller installed
- Docker images pushed to ECR

### 2. Update Configuration

Edit the following files with your values:
- `base/secrets.yaml` - Add your API keys and secrets
- `base/ingress.yaml` - Update domain name
- All deployment files - Update ECR image URIs

### 3. Deploy

**Using PowerShell:**
```powershell
.\k8s\deploy.ps1
```

**Using Bash:**
```bash
chmod +x k8s/deploy.sh
./k8s/deploy.sh
```

**Manual:**
```bash
kubectl apply -f k8s/base/
```

### 4. Create User Instances

```bash
python k8s/user_instance_manager.py create user123
```

## Components

### Base Components (Shared)

- **namespace.yaml**: Creates the `prompt2mesh` namespace
- **configmap.yaml**: Non-sensitive configuration
- **secrets.yaml**: Sensitive credentials (use AWS Secrets Manager in production)
- **postgres-***: PostgreSQL database with persistent storage
- **backend-deployment.yaml**: FastAPI backend (2 replicas)
- **streamlit-deployment.yaml**: Streamlit frontend (2 replicas)
- **blender-deployment.yaml**: Optional shared Blender instance
- **db-init-job.yaml**: One-time database initialization
- **ingress.yaml**: AWS ALB for external access

### Per-User Components

Each user gets:
- **Blender Pod**: Dedicated Blender instance with VNC/Web UI
- **Agent Pod**: User-specific processing agent
- **ConfigMap**: User-specific configuration
- **Service**: Internal networking
- **Ingress**: Subdomain routing (e.g., user-123.prompt2mesh.com)

## Usage

### Deploy Base Infrastructure

```bash
# Deploy everything
kubectl apply -f k8s/base/

# Or step-by-step
kubectl apply -f k8s/base/namespace.yaml
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/configmap.yaml
kubectl apply -f k8s/base/postgres-pvc.yaml
kubectl apply -f k8s/base/postgres-deployment.yaml
kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s
kubectl apply -f k8s/base/db-init-job.yaml
kubectl apply -f k8s/base/backend-deployment.yaml
kubectl apply -f k8s/base/streamlit-deployment.yaml
kubectl apply -f k8s/base/blender-deployment.yaml
kubectl apply -f k8s/base/ingress.yaml
```

### Manage User Instances

```bash
# Create a user instance
python k8s/user_instance_manager.py create user123

# List all user instances
python k8s/user_instance_manager.py list

# Delete a user instance
python k8s/user_instance_manager.py delete user123
```

### Monitor Deployment

```bash
# Check pod status
kubectl get pods -n prompt2mesh

# Check services
kubectl get svc -n prompt2mesh

# Check ingress and get ALB DNS
kubectl get ingress -n prompt2mesh

# View logs
kubectl logs -f deployment/backend -n prompt2mesh
kubectl logs -f deployment/streamlit -n prompt2mesh

# Describe a pod for troubleshooting
kubectl describe pod <pod-name> -n prompt2mesh
```

### Scale Deployments

```bash
# Manual scaling
kubectl scale deployment backend -n prompt2mesh --replicas=5

# Auto-scaling
kubectl autoscale deployment backend -n prompt2mesh --cpu-percent=70 --min=2 --max=10
```

## Configuration

### Environment Variables

Set in `configmap.yaml` and `secrets.yaml`:

**ConfigMap (non-sensitive):**
- `DATABASE_URL`: PostgreSQL connection string
- `BACKEND_URL`: Backend API URL
- `BLENDER_HOST`: Blender service hostname
- `BLENDER_PORT`: Blender MCP server port
- `JWT_EXPIRY_HOURS`: JWT token expiration
- `LANGCHAIN_*`: LangChain/LangSmith configuration

**Secrets (sensitive):**
- `POSTGRES_PASSWORD`: Database password
- `JWT_SECRET_KEY`: JWT signing key
- `ANTHROPIC_API_KEY`: Anthropic API key
- `LANGCHAIN_API_KEY`: LangChain API key
- `LANGSMITH_API_KEY`: LangSmith API key

### Resource Limits

Adjust in deployment files:

```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "2Gi"
    cpu: "2000m"
```

### Storage

PostgreSQL uses a PersistentVolumeClaim with `gp3` storage class (10Gi default).

For production, consider using AWS RDS instead.

## Security

### Best Practices

1. **Use AWS Secrets Manager** instead of Kubernetes Secrets
2. **Enable Network Policies** to isolate user instances
3. **Use RBAC** for access control
4. **Enable Pod Security Standards**
5. **Use private subnets** for pods
6. **Enable ALB access logs**

### Example: External Secrets

```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: prompt2mesh-secrets
  namespace: prompt2mesh
spec:
  secretStoreRef:
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: prompt2mesh-secrets
  data:
    - secretKey: ANTHROPIC_API_KEY
      remoteRef:
        key: prompt2mesh/anthropic-api-key
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n prompt2mesh

# Check logs
kubectl logs <pod-name> -n prompt2mesh

# Check previous logs (if pod crashed)
kubectl logs <pod-name> -n prompt2mesh --previous
```

### Database Connection Issues

```bash
# Test database connectivity
kubectl exec -it deployment/backend -n prompt2mesh -- python3 -c "import psycopg2; psycopg2.connect('postgresql://postgres:postgres@postgres:5432/prompt2mesh_auth')"

# Check postgres logs
kubectl logs deployment/postgres -n prompt2mesh
```

### Ingress Not Working

```bash
# Check ingress status
kubectl describe ingress prompt2mesh-ingress -n prompt2mesh

# Check ALB controller logs
kubectl logs -n kube-system deployment/aws-load-balancer-controller

# Verify security groups allow traffic
```

## Cleanup

### Delete User Instance

```bash
python k8s/user_instance_manager.py delete user123
```

### Delete All Resources

```bash
kubectl delete namespace prompt2mesh
```

## CI/CD

GitHub Actions workflows are available in `.github/workflows/`:

- `build-and-push.yml`: Builds and pushes Docker images to ECR
- `deploy-eks.yml`: Deploys to EKS cluster

Configure secrets in GitHub:
- `AWS_ROLE_ARN`: AWS IAM role for OIDC authentication

## Next Steps

1. Set up monitoring with Prometheus/Grafana
2. Configure automated backups
3. Implement auto-cleanup of idle user instances
4. Add resource quotas per user
5. Set up alerts for critical issues
6. Implement blue-green deployments
