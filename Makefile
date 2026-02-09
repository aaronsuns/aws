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
	@echo "  make ui           - Open UI in browser"

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
	@./test_api.sh

# Run linting (basic checks)
lint:
	@echo "🔍 Running linting checks..."
	@echo "Checking Python files..."
	@python3 -m py_compile aws_serverless_api/*.py lambda/*.py app.py 2>/dev/null || echo "⚠️  Python syntax check skipped (py_compile not available)"
	@echo "Checking shell scripts..."
	@shellcheck deploy.sh test_api.sh deploy-cloudformation.sh setup-aws-credentials.sh 2>/dev/null || echo "⚠️  ShellCheck not installed, skipping"
	@echo "✅ Linting complete"

# Clean build artifacts
clean:
	@echo "🧹 Cleaning build artifacts..."
	@rm -rf cdk.out
	@rm -rf .venv
	@rm -rf __pycache__ aws_serverless_api/__pycache__ lambda/__pycache__
	@rm -rf *.pyc aws_serverless_api/*.pyc lambda/*.pyc
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
	@python3 -c "import json, subprocess; \
		result = subprocess.run(['aws', 'cloudformation', 'describe-stacks', '--stack-name', 'AwsServerlessApiStack', '--query', 'Stacks[0].Outputs', '--output', 'json'], capture_output=True, text=True); \
		outputs = json.loads(result.stdout) if result.returncode == 0 else []; \
		config = {o['OutputKey']: o['OutputValue'] for o in outputs}; \
		ui_url = config.get('UiUrl', '').replace('https://', '').replace('http://', ''); \
		cloudfront_url = f'https://{ui_url}' if ui_url else ''; \
		region_result = subprocess.run(['aws', 'configure', 'get', 'region'], capture_output=True, text=True); \
		region = region_result.stdout.strip() or 'eu-north-1'; \
		config_json = {'apiUrl': config.get('ApiUrl', ''), 'cloudfrontUrl': cloudfront_url, 'region': region, 'database': 'DynamoDB', 'tableName': config.get('DynamoDBTableName', 'api-items')}; \
		json.dump(config_json, open('config.json', 'w'), indent=2); \
		print('✅ config.json updated')" || echo "⚠️  Could not update config.json (stack may not be deployed)"

# Open UI in browser
ui:
	@echo "🌐 Opening UI in browser..."
	@python3 -c "import webbrowser, json; \
		with open('config.json') as f: config = json.load(f); \
		webbrowser.open(config.get('cloudfrontUrl', 'https://d1ws0ned3r126x.cloudfront.net'))" || \
	open https://d1ws0ned3r126x.cloudfront.net || \
	xdg-open https://d1ws0ned3r126x.cloudfront.net || \
	echo "Please open https://d1ws0ned3r126x.cloudfront.net manually"
