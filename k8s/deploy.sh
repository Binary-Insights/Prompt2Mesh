#!/bin/bash
# Deploy all base components to EKS

set -e

echo "Deploying Prompt2Mesh to EKS..."

# Create namespace
echo "Creating namespace..."
kubectl apply -f k8s/base/namespace.yaml

# Apply secrets and config
echo "Applying secrets and config..."
kubectl apply -f k8s/base/secrets.yaml
kubectl apply -f k8s/base/configmap.yaml

# Deploy PostgreSQL
echo "Deploying PostgreSQL..."
kubectl apply -f k8s/base/postgres-pvc.yaml
kubectl apply -f k8s/base/postgres-deployment.yaml

# Wait for postgres
echo "Waiting for PostgreSQL to be ready..."
kubectl wait --for=condition=ready pod -l app=postgres -n prompt2mesh --timeout=300s

# Initialize database
echo "Initializing database..."
kubectl apply -f k8s/base/db-init-job.yaml
kubectl wait --for=condition=complete job/db-init -n prompt2mesh --timeout=300s

# Deploy backend
echo "Deploying backend..."
kubectl apply -f k8s/base/backend-deployment.yaml

# Deploy frontend
echo "Deploying Streamlit frontend..."
kubectl apply -f k8s/base/streamlit-deployment.yaml

# Deploy Blender (optional shared instance)
echo "Deploying Blender..."
kubectl apply -f k8s/base/blender-deployment.yaml

# Deploy ingress
echo "Deploying ingress..."
kubectl apply -f k8s/base/ingress.yaml

echo ""
echo "Deployment complete!"
echo ""
echo "Check status with:"
echo "  kubectl get pods -n prompt2mesh"
echo ""
echo "Get ALB DNS name with:"
echo "  kubectl get ingress prompt2mesh-ingress -n prompt2mesh"
