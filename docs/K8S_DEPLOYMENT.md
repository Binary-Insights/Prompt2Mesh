# Prompt2Mesh Kubernetes Deployment Guide

This guide explains how to deploy Prompt2Mesh on Amazon EKS with per-user Blender pod isolation.

## Architecture

- **Single Backend Pod**: Manages authentication and creates user pods dynamically
- **Single Frontend Pod**: Streamlit UI serving all users
- **Per-User Blender Pods**: Created dynamically on login, destroyed on logout
- **PostgreSQL**: Database for user authentication

## Prerequisites

1. EKS cluster running
2. kubectl configured
3. Docker images pushed to ECR or Docker Hub
4. StorageClass configured (gp2 for AWS EBS)

## Deployment Steps

### 1. Create Namespace

```bash
kubectl create namespace prompt2mesh
kubectl config set-context --current --namespace=prompt2mesh
```

### 2. Create Secrets

```bash
# Create API secrets
kubectl create secret generic api-secrets \
  --from-literal=anthropic-api-key=YOUR_ANTHROPIC_KEY \
  --from-literal=postgres-password=YOUR_DB_PASSWORD

# Create Docker registry secret (if using private registry)
kubectl create secret docker-registry regcred \
  --docker-server=YOUR_REGISTRY \
  --docker-username=YOUR_USERNAME \
  --docker-password=YOUR_PASSWORD
```

### 3. Deploy PostgreSQL

```bash
kubectl apply -f k8s/postgres-deployment.yaml
```

### 4. Deploy Backend

```bash
kubectl apply -f k8s/backend-deployment.yaml
```

### 5. Deploy Frontend

```bash
kubectl apply -f k8s/frontend-deployment.yaml
```

### 6. Expose Services

```bash
kubectl apply -f k8s/ingress.yaml
```

## How It Works

### User Login Flow

1. User logs in via Streamlit frontend
2. Backend creates:
   - Kubernetes Pod for Blender MCP server
   - Kubernetes Service for pod access
   - PVC for persistent storage
3. Pod names: `blender-{username}-{userid}`
4. Service names: `blender-svc-{username}-{userid}`

### User Logout Flow

1. User clicks logout
2. Backend deletes:
   - Blender pod
   - Service
3. PVC is retained for next login

### MCP Connection

Backend connects to user's Blender pod via Kubernetes DNS:
```
blender-svc-{username}-{userid}.{namespace}.svc.cluster.local:9876
```

## Configuration

### Environment Variables (Backend)

- `DEPLOYMENT_MODE=kubernetes` - Enable K8s mode
- `K8S_NAMESPACE=prompt2mesh` - Namespace for user pods
- `BLENDER_IMAGE=prompt2mesh/blender-mcp:latest` - Blender pod image

### RBAC Requirements

Backend needs permissions to:
- Create/delete pods
- Create/delete services  
- Create PVCs
- Read pod status

## Monitoring

```bash
# List all user pods
kubectl get pods -l managed-by=prompt2mesh

# List user services
kubectl get svc -l managed-by=prompt2mesh

# Check backend logs
kubectl logs -f deployment/backend

# Check specific user's pod
kubectl logs blender-username-123
```

## Resource Limits

Per-user pod defaults:
- CPU Request: 500m
- CPU Limit: 2 cores
- Memory Request: 1Gi
- Memory Limit: 4Gi
- Storage: 5Gi PVC

## Scaling

- Backend and Frontend can be horizontally scaled
- User pods are isolated per user
- Database can use RDS for production

## Cleanup

```bash
# Delete user pods
kubectl delete pods -l managed-by=prompt2mesh

# Delete services
kubectl delete svc -l managed-by=prompt2mesh

# Delete PVCs (optional - will lose user data)
kubectl delete pvc -l managed-by=prompt2mesh

# Delete entire deployment
kubectl delete namespace prompt2mesh
```

## Troubleshooting

### Pod Creation Fails
```bash
kubectl describe pod blender-username-123
kubectl logs blender-username-123
```

### Service Connection Issues
```bash
kubectl get svc
kubectl get endpoints
```

### Backend Permissions
```bash
kubectl auth can-i create pods --as=system:serviceaccount:prompt2mesh:backend
```
