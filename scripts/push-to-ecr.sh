#!/bin/bash
# Script to tag and push Docker images to AWS ECR
# Usage: ./push-to-ecr.sh <aws-region> <aws-account-id>

set -e

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <aws-region> <aws-account-id>"
    echo "Example: $0 us-east-1 123456789012"
    exit 1
fi

AWS_REGION=$1
AWS_ACCOUNT_ID=$2
ECR_REGISTRY="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

echo "Authenticating Docker with ECR..."
aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$ECR_REGISTRY"

echo ""
echo "Tagging and pushing images to ECR..."
echo ""

# Backend service
echo "Processing backend image..."
docker tag docker-backend:latest "$ECR_REGISTRY/prompt2mesh/backend:latest"
docker push "$ECR_REGISTRY/prompt2mesh/backend:latest"
echo "✓ Backend image pushed"

# Streamlit service
echo "Processing streamlit image..."
docker tag docker-streamlit:latest "$ECR_REGISTRY/prompt2mesh/streamlit:latest"
docker push "$ECR_REGISTRY/prompt2mesh/streamlit:latest"
echo "✓ Streamlit image pushed"

# DB Init service
echo "Processing db-init image..."
docker tag docker-db-init:latest "$ECR_REGISTRY/prompt2mesh/db-init:latest"
docker push "$ECR_REGISTRY/prompt2mesh/db-init:latest"
echo "✓ DB-init image pushed"

# Blender service (using linuxserver image - optional, for reference)
echo "Processing blender image..."
docker pull linuxserver/blender:latest
docker tag linuxserver/blender:latest "$ECR_REGISTRY/prompt2mesh/blender:latest"
docker push "$ECR_REGISTRY/prompt2mesh/blender:latest"
echo "✓ Blender image pushed"

echo ""
echo "All images successfully pushed to ECR!"
echo ""
echo "Image URIs:"
echo "  - $ECR_REGISTRY/prompt2mesh/backend:latest"
echo "  - $ECR_REGISTRY/prompt2mesh/streamlit:latest"
echo "  - $ECR_REGISTRY/prompt2mesh/db-init:latest"
echo "  - $ECR_REGISTRY/prompt2mesh/blender:latest"
