# Prompt2Mesh EKS Deployment Guide

This directory contains Kubernetes manifests for deploying Prompt2Mesh to Amazon EKS.

## Architecture

The deployment consists of:

### Base Components (Shared)
- **PostgreSQL**: Shared database for all users
- **Backend**: FastAPI backend API (2 replicas)
- **Streamlit**: Frontend UI (2 replicas)
- **Ingress**: AWS ALB for routing traffic

### Per-User Components
- **Blender Instance**: Dedicated Blender container with VNC/Web UI
- **Agent Instance**: User-specific agent for processing requests
- **ConfigMap**: User-specific configuration
- **Service**: Internal networking for user resources
- **Ingress**: User-specific subdomain routing

## Prerequisites

1. **AWS Account** with EKS cluster
2. **kubectl** configured to access your EKS cluster
3. **AWS Load Balancer Controller** installed in your cluster
4. **ECR Repository** for Docker images
5. **External DNS** (optional, for automatic DNS management)
6. **Cert Manager** (optional, for automatic SSL certificates)

## Setup Steps

### 1. Build and Push Docker Images

```bash
# Set your AWS account ID and region
export AWS_ACCOUNT_ID=<your-account-id>
export AWS_REGION=<your-region>

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Create ECR repositories
aws ecr create-repository --repository-name prompt2mesh-backend --region $AWS_REGION
aws ecr create-repository --repository-name prompt2mesh-streamlit --region $AWS_REGION

# Build and push backend image
docker build -t prompt2mesh-backend:latest -f docker/dockerfile --target backend .
docker tag prompt2mesh-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-backend:latest

# Build and push streamlit image (same as backend but different command)
docker tag prompt2mesh-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/prompt2mesh-streamlit:latest
```

### 2. Update Image URIs

Update the image URIs in the following files:
- `k8s/base/backend-deployment.yaml`
- `k8s/base/streamlit-deployment.yaml`
- `k8s/base/db-init-job.yaml`
- `k8s/per-user/user-instance-template.yaml`

Replace `<AWS_ACCOUNT_ID>` and `<AWS_REGION>` with your actual values.

### 3. Update Secrets

Edit `k8s/base/secrets.yaml` and add your actual secrets:
```yaml
stringData:
  POSTGRES_PASSWORD: <your-secure-password>
  JWT_SECRET_KEY: <your-jwt-secret>
  ANTHROPIC_API_KEY: <your-anthropic-key>
  LANGCHAIN_API_KEY: <your-langchain-key>
  LANGSMITH_API_KEY: <your-langsmith-key>
```

**Production Recommendation**: Use AWS Secrets Manager with External Secrets Operator instead of storing secrets in YAML.

### 4. Deploy Base Components

```bash
# Create namespace
kubectl apply -f k8s/base/namespace.yaml

# Apply secrets and config
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/configmap.yaml

# Deploy PostgreSQL
kubectl apply -f k8s/base/postgres-pvc.yaml
kubectl apply -f k8s/base/postgres-deployment.yaml

# Wait for postgres to be ready
kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s

# Initialize database
kubectl apply -f k8s/base/db-init-job.yaml

# Wait for db-init to complete
kubectl wait --for=condition=complete job/db-init -n prompt2mesh --timeout=300s

# Deploy backend and frontend
kubectl apply -f k8s/base/backend-deployment.yaml
kubectl apply -f k8s/base/streamlit-deployment.yaml

# Deploy shared Blender instance (optional)
kubectl apply -f k8s/base/blender-deployment.yaml

# Deploy ingress
kubectl apply -f k8s/base/ingress.yaml
```

### 5. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n prompt2mesh

# Check services
kubectl get svc -n prompt2mesh

# Check ingress
kubectl get ingress -n prompt2mesh

# Get ALB DNS name
kubectl get ingress prompt2mesh-ingress -n prompt2mesh -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

### 6. Configure DNS

Point your domain to the ALB DNS name:
```
prompt2mesh.example.com -> <alb-dns-name>
*.prompt2mesh.example.com -> <alb-dns-name>  (for per-user subdomains)
```

## Per-User Instance Management

### Create User Instance

```bash
# Using Python script
python k8s/user_instance_manager.py create user123

# Or manually with kubectl
sed 's/{{ USER_ID }}/user123/g' k8s/per-user/user-instance-template.yaml | kubectl apply -f -
```

This creates:
- Blender instance at `http://user-user123.prompt2mesh.example.com/blender`
- Agent instance at `http://user-user123.prompt2mesh.example.com/agent`

### Delete User Instance

```bash
# Using Python script
python k8s/user_instance_manager.py delete user123

# Or manually with kubectl
sed 's/{{ USER_ID }}/user123/g' k8s/per-user/user-instance-template.yaml | kubectl delete -f -
```

### List User Instances

```bash
python k8s/user_instance_manager.py list

# Or with kubectl
kubectl get pods -n prompt2mesh -l app=blender
kubectl get pods -n prompt2mesh -l app=agent
```

## Scaling

### Horizontal Pod Autoscaler (HPA)

```bash
# Auto-scale backend based on CPU
kubectl autoscale deployment backend -n prompt2mesh --cpu-percent=70 --min=2 --max=10

# Auto-scale streamlit based on CPU
kubectl autoscale deployment streamlit -n prompt2mesh --cpu-percent=70 --min=2 --max=10
```

### Cluster Autoscaler

Ensure Cluster Autoscaler is installed for automatic node scaling:
```bash
# Configure Cluster Autoscaler (EKS-specific)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/autoscaler/master/cluster-autoscaler/cloudprovider/aws/examples/cluster-autoscaler-autodiscover.yaml
```

## Monitoring

### Prometheus & Grafana

```bash
# Install Prometheus & Grafana via Helm
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace
```

### CloudWatch Container Insights

```bash
# Deploy CloudWatch agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/quickstart/cwagent-fluentd-quickstart.yaml
```

## Cost Optimization

1. **Use Spot Instances**: Configure node groups with spot instances for cost savings
2. **Right-size Resources**: Adjust resource requests/limits based on actual usage
3. **Auto-scaling**: Enable HPA and Cluster Autoscaler
4. **Cleanup Idle Resources**: Implement automated cleanup of unused user instances

## Troubleshooting

### Check Pod Logs

```bash
kubectl logs -f deployment/backend -n prompt2mesh
kubectl logs -f deployment/streamlit -n prompt2mesh
kubectl logs -f deployment/blender-user123 -n prompt2mesh
```

### Debug Pod Issues

```bash
kubectl describe pod <pod-name> -n prompt2mesh
kubectl get events -n prompt2mesh --sort-by='.lastTimestamp'
```

### Access Pod Shell

```bash
kubectl exec -it deployment/backend -n prompt2mesh -- /bin/bash
```

## Security Best Practices

1. **Use AWS Secrets Manager** with External Secrets Operator
2. **Enable Network Policies** to isolate user instances
3. **Use RBAC** to restrict permissions
4. **Enable Pod Security Standards**
5. **Regularly update images** for security patches
6. **Use private subnets** for pods
7. **Enable VPC Flow Logs** for network monitoring

## Backup and Disaster Recovery

### Database Backups

```bash
# Manual backup
kubectl exec -n prompt2mesh deployment/postgres -- pg_dump -U postgres prompt2mesh_auth > backup.sql

# Restore
kubectl exec -i -n prompt2mesh deployment/postgres -- psql -U postgres prompt2mesh_auth < backup.sql
```

### Automated Backups

Use AWS RDS instead of in-cluster PostgreSQL for production:
- Automated backups
- Point-in-time recovery
- Multi-AZ deployment
- Better performance

## Next Steps

1. **Implement User Session Management**: Track active users and cleanup idle instances
2. **Add Resource Quotas**: Limit resources per user
3. **Implement Rate Limiting**: Prevent abuse
4. **Add Monitoring Dashboards**: Create custom dashboards for user metrics
5. **CI/CD Pipeline**: Automate image builds and deployments
6. **Blue-Green Deployments**: Zero-downtime updates
