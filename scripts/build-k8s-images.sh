#!/bin/bash
# Build and push Docker images for Kubernetes deployment

set -e

# Configuration
REGISTRY=${DOCKER_REGISTRY:-"prompt2mesh"}  # Change to your registry
TAG=${IMAGE_TAG:-"latest"}

echo "🐳 Building Docker images..."

# Build backend
echo "📦 Building backend image..."
docker build -f Dockerfile.backend -t ${REGISTRY}/backend:${TAG} .

# Build frontend
echo "📦 Building frontend image..."
docker build -f Dockerfile.frontend -t ${REGISTRY}/frontend:${TAG} .

# Build Blender MCP (reuse existing)
echo "📦 Building Blender MCP image..."
cd docker/blender-with-mcp
docker build -t ${REGISTRY}/blender-mcp:${TAG} .
cd ../..

echo "✅ All images built successfully!"

# Push to registry (optional)
read -p "Push images to registry? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "🚀 Pushing images to ${REGISTRY}..."
    docker push ${REGISTRY}/backend:${TAG}
    docker push ${REGISTRY}/frontend:${TAG}
    docker push ${REGISTRY}/blender-mcp:${TAG}
    echo "✅ Images pushed successfully!"
fi

echo ""
echo "📝 Update your k8s/*.yaml files with:"
echo "   Backend image: ${REGISTRY}/backend:${TAG}"
echo "   Frontend image: ${REGISTRY}/frontend:${TAG}"
echo "   Blender image: ${REGISTRY}/blender-mcp:${TAG}"
