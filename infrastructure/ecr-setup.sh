#!/bin/bash
# ECR Setup Script - Create repositories for all Prompt2Mesh services
# Usage: ./ecr-setup.sh <aws-region> <aws-account-id>

set -e

# Check arguments
if [ $# -ne 2 ]; then
    echo "Usage: $0 <aws-region> <aws-account-id>"
    echo "Example: $0 us-east-1 123456789012"
    exit 1
fi

AWS_REGION=$1
AWS_ACCOUNT_ID=$2

echo "Creating ECR repositories in region: $AWS_REGION"
echo "AWS Account ID: $AWS_ACCOUNT_ID"
echo ""

# Array of repository names
REPOS=(
    "prompt2mesh/backend"
    "prompt2mesh/streamlit"
    "prompt2mesh/blender"
    "prompt2mesh/db-init"
)

# Create each repository
for REPO in "${REPOS[@]}"; do
    echo "Creating repository: $REPO"
    aws ecr create-repository \
        --repository-name "$REPO" \
        --region "$AWS_REGION" \
        --image-scanning-configuration scanOnPush=true \
        --encryption-configuration encryptionType=AES256 \
        2>&1 | grep -v "RepositoryAlreadyExistsException" || true
    
    echo "✓ Repository $REPO created or already exists"
done

echo ""
echo "ECR repositories created successfully!"
echo ""
echo "Repository URIs:"
for REPO in "${REPOS[@]}"; do
    echo "  - $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$REPO"
done
