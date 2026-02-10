# AWS Test Repository

A collection of AWS test projects and scripts for experimenting with AWS services.

## What's in this repo

- **Serverless API** - API Gateway HTTP API + Lambda (Python) + DynamoDB with CRUD operations
- **DynamoDB** - NoSQL database (FREE TIER: 25 GB storage, 25 WCU, 25 RCU)
- **Deployment scripts** - CDK and CloudFormation deployment options
- **Test scripts** - API testing utilities with CRUD test cases
- **Web UI** - Simple HTML interface for testing CRUD operations
- **Infrastructure as Code** - CDK (Python) and CloudFormation templates

## Quick Start

1. Configure AWS credentials:
   ```bash
   aws configure
   ```

2. Deploy the serverless API:
   ```bash
   make deploy
   # or: yarn deploy / npm run deploy
   ```

3. Test the API:
   ```bash
   make test
   # or: yarn test / npm test
   ```

4. Use the Web UI:
   ```bash
   make ui
   # Opens the UI in your browser automatically
   ```

## Available Commands

Similar to npm/yarn scripts, use `make` commands (or `yarn`/`npm run`):

**Using Make (recommended):**
```bash
make install      # Install Python dependencies
make deploy       # Deploy the CDK stack
make test         # Run API tests
make lint         # Run linting checks
make build        # Build/synthesize CDK stack
make clean        # Clean build artifacts
make destroy      # Destroy the CDK stack
make bootstrap    # Bootstrap CDK (first time setup)
make setup-urls   # Update config.json with deployed URLs
make ui           # Open UI in browser
make help         # Show all available commands
```

**Using Yarn/NPM (alternative):**
```bash
yarn install      # or: npm run install
yarn deploy       # or: npm run deploy
yarn test         # or: npm test
yarn lint         # or: npm run lint
yarn build        # or: npm run build
yarn clean        # or: npm run clean
yarn destroy      # or: npm run destroy
yarn bootstrap    # or: npm run bootstrap
yarn setup-urls   # or: npm run setup-urls
yarn ui           # or: npm run ui
```

## Project Structure

```
├── app.py                          # CDK app entry point
├── video_processing/               # CDK stack definitions (Video processing with Lambda + Step Functions)
├── lambda/                         # Lambda function code with CRUD operations
│   ├── handler.py                  # Main Lambda handler
│   └── requirements.txt            # Lambda dependencies (boto3 for DynamoDB)
├── ui/                             # Web UI for testing
│   └── index.html                  # HTML interface for CRUD operations
├── deploy.sh                       # CDK deployment script
├── deploy-cloudformation.sh        # CloudFormation deployment script
├── test_api.sh                     # API testing script with CRUD tests
├── cloudformation-template.yaml    # CloudFormation template
└── requirements.txt                # CDK Python dependencies
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
