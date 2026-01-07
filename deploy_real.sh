#!/bin/bash
set -e

# Configuration
REGION="us-east-1"
TAG="real-v1"

echo "=== Deploying Real MCP Server (Container) ==="

# 1. Get ECR Repository URL from Terraform
echo "Getting ECR Repository URL..."
cd nemo-infrastructure
REPO_URL=$(terraform output -raw mcp_ecr_repository_url)
cd ..
echo "Target Repository: $REPO_URL"

# 2. Authenticate Docker to ECR
echo "Authenticating to ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REPO_URL

# 3. Build Real Image (using mcp_server_py/Dockerfile)
echo "Building Real Image..."
docker build -t $REPO_URL:$TAG -f mcp_server_py/Dockerfile .

# 4. Push to ECR
echo "Pushing to ECR..."
docker push $REPO_URL:$TAG

# 5. Apply Terraform (which should now point to this tag)
echo "Updating Infrastructure..."
cd nemo-infrastructure
terraform apply -auto-approve
cd ..

echo "=== Deployment Complete ==="
echo "Real server deployed with tag: $TAG"
