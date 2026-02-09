#!/bin/bash

# CloudFormation Deployment Script
# Alternative to CDK - uses CloudFormation directly

set -e  # Exit on error

echo "🚀 AWS Serverless API Deployment (CloudFormation)"
echo "=================================================="
echo ""

# Check if AWS credentials are configured
echo "📋 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured!"
    echo "Please run: aws configure"
    exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
STACK_NAME="serverless-api-stack"

echo "✅ AWS Account: $ACCOUNT"
echo "✅ AWS Region: $REGION"
echo "✅ Stack Name: $STACK_NAME"
echo ""

# Check if stack exists
if aws cloudformation describe-stacks --stack-name "$STACK_NAME" &> /dev/null; then
    echo "📋 Stack exists. Updating..."
    OPERATION="update"
else
    echo "📋 Stack does not exist. Creating..."
    OPERATION="create"
fi

# Deploy CloudFormation stack
echo "🚀 Deploying CloudFormation stack..."
aws cloudformation "$OPERATION-stack" \
    --stack-name "$STACK_NAME" \
    --template-body file://cloudformation-template.yaml \
    --capabilities CAPABILITY_NAMED_IAM \
    --region "$REGION"

echo "⏳ Waiting for stack operation to complete..."
aws cloudformation wait stack-"${OPERATION}-complete" \
    --stack-name "$STACK_NAME" \
    --region "$REGION"

echo "✅ Stack operation complete!"
echo ""

# Get outputs
echo "📝 Stack Outputs:"
aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region "$REGION"

echo ""
echo "🧹 To cleanup: aws cloudformation delete-stack --stack-name $STACK_NAME"
