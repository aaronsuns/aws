# AWS Test Repository

A collection of AWS test projects and scripts for experimenting with AWS services.

## What's in this repo

- **Serverless API** - API Gateway HTTP API + Lambda (Python) setup using CDK
- **Deployment scripts** - CDK and CloudFormation deployment options
- **Test scripts** - API testing utilities
- **Infrastructure as Code** - CDK (Python) and CloudFormation templates

## Quick Start

1. Configure AWS credentials:
   ```bash
   aws configure
   ```

2. Deploy the serverless API:
   ```bash
   ./deploy.sh
   ```

3. Test the API:
   ```bash
   ./test_api.sh
   ```

## Project Structure

```
├── app.py                          # CDK app entry point
├── aws_serverless_api/             # CDK stack definitions
├── lambda/                         # Lambda function code
├── deploy.sh                       # CDK deployment script
├── deploy-cloudformation.sh        # CloudFormation deployment script
├── test_api.sh                     # API testing script
├── cloudformation-template.yaml    # CloudFormation template
└── requirements.txt                # Python dependencies
```

## Requirements

- AWS account with credentials configured
- Python 3.8+
- Node.js (for CDK)
- AWS CDK CLI: `npm install -g aws-cdk`

## Cleanup

Remove all resources:
```bash
cdk destroy
```
