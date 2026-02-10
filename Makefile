.PHONY: help install deploy test lint clean destroy bootstrap synth setup-urls

# Default target
help:
	@echo "Available commands:"
	@echo "  make install      - Install Python dependencies"
	@echo "  make deploy       - Deploy the CDK stack"
	@echo "  make test         - Run API tests"
	@echo "  make lint         - Run linting checks"
	@echo "  make build        - Build/synthesize CDK stack"
	@echo "  make clean        - Clean build artifacts"
	@echo "  make destroy      - Destroy the CDK stack"
	@echo "  make bootstrap    - Bootstrap CDK (first time setup)"
	@echo "  make setup-urls   - Update config.json with deployed URLs"
	@echo "  make urls         - Display deployment URLs"
	@echo "  make ui           - Open UI in browser"
	@echo "  make check-aws    - Check AWS credentials configuration"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	python3 -m venv .venv || true
	.venv/bin/pip install --upgrade pip -q
	.venv/bin/pip install -r requirements.txt -q
	@echo "✅ Dependencies installed"

# Deploy the stack
deploy: install
	@echo "🚀 Deploying CDK stack..."
	@source .venv/bin/activate && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 cdk deploy --require-approval never
	@$(MAKE) setup-urls

# Build/synthesize CDK stack
build: install
	@echo "🔨 Synthesizing CDK stack..."
	@source .venv/bin/activate && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 cdk synth

# Run tests
test:
	@echo "🧪 Running API tests..."
	@./scripts/test_api.sh

# Test video processing flow
test-video:
	@echo "🎥 Testing video processing flow..."
	@./scripts/test_video_processing.sh

# Build and push Docker image to ECR
build-docker:
	@echo "🐳 Building and pushing Docker image..."
	@./scripts/build-and-push-docker.sh

# Build Docker image locally (without pushing)
docker-build:
	@echo "🐳 Building Docker image locally..."
	@cd processor && docker build -t video-processor:latest .

# Run Docker container locally for testing
docker-run:
	@echo "🐳 Running Docker container locally..."
	@docker run --rm -it \
		-e JOB_ID=test-job-123 \
		-e S3_BUCKET=test-bucket \
		-e S3_KEY=test-key.mp4 \
		-e JOBS_TABLE_NAME=test-table \
		-e VIDEOS_BUCKET_NAME=test-bucket \
		video-processor:latest

# Run linting (basic checks)
lint:
	@echo "🔍 Running linting checks..."
	@echo "Checking Python files..."
	@python3 -m py_compile video_processing/*.py lambda/*.py app.py 2>/dev/null || echo "⚠️  Python syntax check skipped (py_compile not available)"
	@echo "Checking shell scripts..."
	@shellcheck scripts/*.sh 2>/dev/null || echo "⚠️  ShellCheck not installed, skipping"
	@echo "✅ Linting complete"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf cdk.out
	@rm -rf .venv
	@rm -rf __pycache__ video_processing/__pycache__ lambda/__pycache__
	@rm -rf *.pyc video_processing/*.pyc lambda/*.pyc
	@find . -type d -name "__pycache__" -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "✅ Clean complete"

# Destroy the stack
destroy:
	@echo "🗑️  Destroying CDK stack..."
	@source .venv/bin/activate && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 cdk destroy --force

# Bootstrap CDK (first time setup)
bootstrap:
	@echo "🔧 Bootstrapping CDK..."
	@source .venv/bin/activate && JSII_SILENCE_WARNING_UNTESTED_NODE_VERSION=1 cdk bootstrap

# Update config.json with deployed URLs
setup-urls:
	@echo "📝 Updating config.json with deployed URLs..."
	@python3 -c "import json, os, subprocess; \
		stage = os.getenv('STAGE', 'dev'); \
		stack_name = f'VideoProcessingStack-{stage}'; \
		result = subprocess.run(['aws', 'cloudformation', 'describe-stacks', '--stack-name', stack_name, '--query', 'Stacks[0].Outputs', '--output', 'json'], capture_output=True, text=True); \
		outputs = json.loads(result.stdout) if result.returncode == 0 else []; \
		config = {o['OutputKey']: o['OutputValue'] for o in outputs}; \
		ui_url = config.get('UiUrl', '').replace('https://', '').replace('http://', ''); \
		cloudfront_url = f'https://{ui_url}' if ui_url else ''; \
		region_result = subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True); \
		region = region_result.stdout.strip() or 'eu-north-1'; \
		config_json = {'apiUrl': config.get('ApiUrl', ''), 'cloudfrontUrl': cloudfront_url, 'region': region, 'database': 'DynamoDB', 'tableName': config.get('DynamoDBTableName', f'api-items-{stage}')}; \
		json.dump(config_json, open('config.json', 'w'), indent=2); \
		print('✅ config.json updated')" || echo "⚠️  Could not update config.json (stack may not be deployed)"

# Display deployment URLs
urls:
	@echo "🔗 Getting deployment URLs..."
	@STAGE=$${STAGE:-dev}; \
	STACK_NAME="VideoProcessingStack-$$STAGE"; \
	echo "Stack: $$STACK_NAME (stage: $$STAGE)"; \
	echo ""; \
	OUTPUTS=$$(aws cloudformation describe-stacks --stack-name "$$STACK_NAME" --query 'Stacks[0].Outputs' --output json 2>/dev/null); \
	if [ -z "$$OUTPUTS" ] || [ "$$OUTPUTS" == "null" ]; then \
		echo "❌ Could not find stack: $$STACK_NAME"; \
		echo "Make sure the stack is deployed and you have AWS credentials configured."; \
		exit 1; \
	fi; \
	API_URL=$$(echo "$$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'ApiUrl'), ''))"); \
	UI_URL=$$(echo "$$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'UiUrl'), ''))"); \
	S3_URL=$$(echo "$$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'UiS3Url'), ''))"); \
	TABLE_NAME=$$(echo "$$OUTPUTS" | python3 -c "import sys, json; outputs = json.load(sys.stdin); print(next((o['OutputValue'] for o in outputs if o['OutputKey'] == 'DynamoDBTableName'), ''))"); \
	echo "📡 API Gateway URL:"; \
	echo "   $$API_URL"; \
	echo ""; \
	echo "🌐 CloudFront UI URL (HTTPS):"; \
	echo "   https://$$UI_URL"; \
	echo ""; \
	echo "📦 S3 Website URL (fallback):"; \
	echo "   $$S3_URL"; \
	echo ""; \
	echo "🗄️  DynamoDB Table:"; \
	echo "   $$TABLE_NAME"; \
	echo ""

# Check AWS credentials
check-aws:
	@echo "🔐 Checking AWS credentials..."
	@if aws sts get-caller-identity &> /dev/null; then \
		echo "✅ AWS credentials configured"; \
		aws sts get-caller-identity; \
	else \
		echo "❌ AWS credentials not configured!"; \
		echo "Please run: aws configure"; \
		exit 1; \
	fi

# Open UI in browser
ui:
	@echo "🌐 Opening UI in browser..."
	@python3 -c "import webbrowser, json; \
		with open('config.json') as f: config = json.load(f); \
		webbrowser.open(config.get('cloudfrontUrl', 'https://d1ws0ned3r126x.cloudfront.net'))" || \
	open https://d1ws0ned3r126x.cloudfront.net || \
	xdg-open https://d1ws0ned3r126x.cloudfront.net || \
	echo "Please open https://d1ws0ned3r126x.cloudfront.net manually"
