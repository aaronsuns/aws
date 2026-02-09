#!/bin/bash

# AWS Serverless API Deployment Script
# This script helps deploy the serverless API using CDK

set -e  # Exit on error

echo "🚀 AWS Serverless API Deployment Script"
echo "========================================"
echo ""

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "⚠️  Virtual environment not activated. Activating now..."
    source .venv/bin/activate
fi

# Check if AWS credentials are configured
echo "📋 Checking AWS credentials..."
if ! aws sts get-caller-identity &> /dev/null; then
    echo "❌ AWS credentials not configured!"
    echo "Please run: aws configure"
    exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")
echo "✅ AWS Account: $ACCOUNT"
echo "✅ AWS Region: $REGION"
echo ""

# Check if CDK is installed
echo "📋 Checking CDK installation..."
if ! command -v cdk &> /dev/null; then
    echo "❌ CDK not installed!"
    echo "Please run: npm install -g aws-cdk"
    exit 1
fi
echo "✅ CDK installed: $(cdk --version)"
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt
echo "✅ Dependencies installed"
echo ""

# Check if CDK is bootstrapped
echo "📋 Checking CDK bootstrap status..."
if ! aws cloudformation describe-stacks --stack-name CDKToolkit &> /dev/null; then
    echo "⚠️  CDK not bootstrapped. Bootstrapping now..."
    cdk bootstrap
    echo "✅ CDK bootstrapped"
else
    echo "✅ CDK already bootstrapped"
fi
echo ""

# Synthesize CloudFormation template
echo "🔨 Synthesizing CloudFormation template..."
cdk synth
echo "✅ Template synthesized"
echo ""

# Deploy
echo "🚀 Deploying to AWS..."
read -p "Continue with deployment? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    cdk deploy --require-approval never
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📝 Next steps:"
    echo "   1. Get your API URL from the CDK output above"
    echo "   2. Test with: curl <API_URL>"
    echo "   3. Monitor costs: https://console.aws.amazon.com/cost-management/home"
    echo ""
    echo "🧹 To cleanup: cdk destroy"
else
    echo "❌ Deployment cancelled"
    exit 1
fi
