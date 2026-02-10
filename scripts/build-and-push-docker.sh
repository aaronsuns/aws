#!/bin/bash
# Build and push Docker image to ECR

set -e

STAGE="${STAGE:-dev}"
REGION="${AWS_DEFAULT_REGION:-eu-north-1}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

if [ -z "$ACCOUNT_ID" ]; then
    echo "Error: Could not get AWS account ID"
    exit 1
fi

ECR_REPO_NAME="video-processor-${STAGE}"
ECR_REPO_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${ECR_REPO_NAME}"

echo "Building Docker image..."
cd processor
docker build -t "${ECR_REPO_NAME}:latest" .

echo "Logging in to ECR..."
aws ecr get-login-password --region "${REGION}" | \
    docker login --username AWS --password-stdin "${ECR_REPO_URI}"

echo "Tagging image..."
docker tag "${ECR_REPO_NAME}:latest" "${ECR_REPO_URI}:latest"

echo "Pushing image to ECR..."
docker push "${ECR_REPO_URI}:latest"

echo "✅ Image pushed successfully: ${ECR_REPO_URI}:latest"
cd ..
