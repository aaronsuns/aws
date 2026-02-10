# AWS Serverless Video Processing Pipeline

A serverless video processing pipeline built on AWS using CDK (Python), featuring API Gateway, Lambda, DynamoDB, S3, SQS, and Step Functions. This project demonstrates an event-driven architecture for asynchronous video processing with job tracking and a web UI.

## Features

- **RESTful API** - HTTP API Gateway with Lambda handlers for CRUD operations and job management
- **Video Processing Pipeline** - Asynchronous video processing workflow using Step Functions
- **Job Tracking** - DynamoDB-based job status tracking with progress monitoring
- **File Upload** - Direct browser-to-S3 uploads with presigned URLs
- **Web UI** - Two-page interface for items management and video processing jobs
- **Event-Driven Architecture** - S3 events → SQS → Step Functions → Lambda processing
- **Infrastructure as Code** - AWS CDK (Python) for all infrastructure

## Architecture

```
┌─────────┐
│ Browser │
└────┬────┘
     │
     ▼
┌─────────────────┐
│  API Gateway    │
│  (HTTP API)     │
└────┬────────────┘
     │
     ▼
┌─────────────────┐      ┌──────────────┐
│  Lambda Handler │─────▶│  DynamoDB    │
│  (API Routes)   │      │  (Items/Jobs)│
└─────────────────┘      └──────────────┘
     │
     │ POST /jobs
     ▼
┌─────────────────┐
│ Generate        │
│ Presigned URL   │
└─────────────────┘
     │
     │ Upload File
     ▼
┌──────────────┐
│  S3 Bucket   │
│  (Videos)    │
└──────┬───────┘
       │
       │ Event Notification
       ▼
┌──────────────┐
│  SQS Queue   │
└──────┬───────┘
       │
       │ Trigger
       ▼
┌─────────────────────┐
│ Step Functions      │
│ State Machine       │
└──────┬──────────────┘
       │
       │ Invoke
       ▼
┌─────────────────────┐
│ Lambda Processor    │
│ (Video Processing)  │
└──────┬──────────────┘
       │
       │ Update Status
       ▼
┌──────────────┐
│  DynamoDB    │
│  (Jobs)      │
└──────────────┘
```

## AWS Services Used

- **API Gateway (HTTP API)** - RESTful API endpoints
- **Lambda** - Serverless compute for API handlers and video processing
- **DynamoDB** - NoSQL database for items and job tracking
- **S3** - Object storage for video files and static web UI
- **SQS** - Message queue for event processing
- **Step Functions** - Workflow orchestration for video processing
- **CloudFront** - CDN for web UI distribution
- **CloudWatch Logs** - Logging and monitoring

## Free Tier Eligibility

This project is designed to stay within AWS Free Tier limits:
- **Lambda**: 1M requests/month, 400K GB-seconds
- **DynamoDB**: 25 GB storage, 25 WCU, 25 RCU
- **S3**: 5 GB storage, 2K PUT requests/month
- **SQS**: 1M requests/month
- **Step Functions**: 4K state transitions/month
- **API Gateway**: 1M requests/month

## Quick Start

### Prerequisites

- AWS account with credentials configured
- Python 3.8+
- Node.js (for CDK)
- AWS CDK CLI: `npm install -g aws-cdk`

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd aws
   ```

2. Install dependencies:
   ```bash
   make install
   ```

3. Configure AWS credentials:
   ```bash
   aws configure
   ```

4. Bootstrap CDK (first time only):
   ```bash
   make bootstrap
   ```

### Deployment

Deploy the entire stack:
```bash
STAGE=dev make deploy
```

This will:
- Deploy all AWS resources (API Gateway, Lambda, DynamoDB, S3, SQS, Step Functions)
- Deploy the web UI to S3 with CloudFront
- Update `config.json` with deployed URLs

### Testing

Run lint and unit tests (recommended before pushing):
```bash
make quality
```

Test the API endpoints (against a deployed stack):
```bash
make test
```

Test the full video processing pipeline (create job → upload to S3 → processing → COMPLETED):
```bash
make test-video
```
The script aborts if the S3 upload fails (e.g. 403); the pipeline must be deployed and working for the test to complete.

### Access the Web UI

After deployment, get the UI URL:
```bash
make setup-urls
cat config.json
```

Or open directly:
```bash
make ui
```

## Available Commands

```bash
make install      # Install Python dependencies
make install-dev  # Install dev dependencies (ruff, pytest) for lint and unit tests
make deploy       # Deploy the CDK stack
make test         # Run API tests (against deployed stack)
make test-unit    # Run Python unit tests (pytest)
make test-video   # Test video processing flow (create job, upload, poll status)
make lint         # Run Python linting (ruff) and shell script checks (shellcheck)
make quality      # Run lint and unit tests (use before pushing)
make build        # Build/synthesize CDK stack
make build-docker # Build and push Docker image to ECR (for ECS reference)
make clean        # Clean build artifacts
make destroy      # Destroy the CDK stack
make bootstrap    # Bootstrap CDK (first time setup)
make setup-urls   # Update config.json with deployed URLs
make urls         # Display deployment URLs (API, UI, table name)
make check-aws    # Check AWS credentials
make ui           # Open UI in browser
make help         # Show all available commands
```

## Development and Quality

- **Lint**: `make lint` runs [Ruff](https://docs.astral.sh/ruff/) (check + format) on `app.py`, `video_processing/`, and `lambda/`, and optionally [ShellCheck](https://www.shellcheck.net/) on `scripts/*.sh`.
- **Unit tests**: `make test-unit` runs pytest in `tests/` (see `tests/test_jobs_service.py`, `tests/test_items_service.py`). Requires `make install-dev`.
- **Quality**: `make quality` runs lint then unit tests; use before committing or pushing.
- **CI**: GitHub Actions (`.github/workflows/ci.yml`) runs `make quality` on push and pull requests to `main`.

## Project Structure

```
├── app.py                          # CDK app entry point
├── video_processing/               # CDK stack definitions
│   └── video_processing_stack.py   # Main stack with all resources
├── lambda/                         # Lambda function code
│   ├── handler.py                  # API Gateway handler (CRUD + Jobs)
│   ├── processor.py                # Video processing Lambda
│   ├── step_function_trigger.py    # Step Functions trigger Lambda
│   ├── repositories/               # Data access layer
│   │   ├── items_repository.py     # DynamoDB access for items
│   │   └── jobs_repository.py      # DynamoDB access for jobs
│   ├── services/                   # Business logic layer
│   │   ├── items_service.py        # Items business logic
│   │   └── jobs_service.py         # Jobs business logic
│   └── requirements.txt            # Lambda dependencies
├── ui/                             # Web UI
│   ├── index.html                  # Items management page
│   └── jobs.html                   # Video processing jobs page
├── processor/                      # ECS processor (reference, unused)
│   ├── Dockerfile                  # Docker image definition
│   └── processor.py                # Containerized processor
├── scripts/                        # Shell scripts
│   ├── test_api.sh                 # API testing script
│   ├── test_video_processing.sh    # Video processing test script
│   └── build-and-push-docker.sh    # Docker build script (for ECS)
├── tests/                          # Python unit tests (pytest)
│   ├── conftest.py                 # Pytest fixtures and env for lambda imports
│   ├── test_jobs_service.py        # Jobs service tests
│   └── test_items_service.py       # Items service tests
├── Makefile                        # Build automation
├── requirements.txt                # CDK Python dependencies
├── requirements-dev.txt            # Dev dependencies (ruff, pytest)
├── pyproject.toml                  # Ruff and pytest config
└── .github/workflows/ci.yml         # GitHub Actions (lint + unit tests)
```

## API Endpoints

### Items Management

- `GET /` - API information
- `GET /items` - List all items
- `POST /items` - Create new item
- `GET /items/{id}` - Get item by ID
- `PUT /items/{id}` - Update item
- `DELETE /items/{id}` - Delete item

### Video Processing Jobs

- `POST /jobs` - Create job and get presigned upload URL
  ```json
  {
    "filename": "video.mp4"
  }
  ```
  Returns:
  ```json
  {
    "job_id": "uuid",
    "presigned_url": "https://...",
    "status": "PENDING",
    "s3_key": "uploads/uuid/video.mp4"
  }
  ```

- `GET /jobs/{id}` - Get job status
  Returns:
  ```json
  {
    "job_id": "uuid",
    "status": "PENDING|PROCESSING|COMPLETED|FAILED",
    "filename": "video.mp4",
    "progress_percent": 75,
    "results": { ... },
    "created_at": "2026-02-10T...",
    "updated_at": "2026-02-10T..."
  }
  ```

## Video Processing Flow

1. **Create Job**: Client calls `POST /jobs` with filename
2. **Get Presigned URL**: Server generates S3 presigned URL for upload
3. **Upload File**: Client uploads file directly to S3 using presigned URL
4. **S3 Event**: S3 sends event notification to SQS queue
5. **Trigger Step Functions**: Lambda reads from SQS and starts Step Functions execution
6. **Process Video**: Step Functions invokes processing Lambda
7. **Update Status**: Processing Lambda updates job status in DynamoDB
8. **Poll Status**: Client polls `GET /jobs/{id}` to check progress

## Web UI Features

### Items Page (`index.html`)
- Create, read, update, delete items
- Real-time item list updates
- Form validation and error handling

### Jobs Page (`jobs.html`)
- File upload with drag-and-drop support
- Create video processing jobs
- Real-time job status monitoring
- Auto-refresh for processing jobs
- Progress bar visualization
- Results display

## Monitoring and Logging

All API calls are logged to CloudWatch Logs with full request details:
- HTTP method and full URL
- Path and query parameters
- Request body
- Response status

View logs:
```bash
aws logs tail /aws/lambda/VideoProcessingStack-dev-ApiHandler --follow
```

## Environment Variables

The stack uses the `STAGE` environment variable:
- `STAGE=dev` (default) - Development environment
- `STAGE=stage` - Staging environment
- `STAGE=prod` - Production environment

## Cleanup

To remove all resources:
```bash
make destroy
```

Or manually:
```bash
cdk destroy VideoProcessingStack-dev
```

## Notes

- **Video Processing**: Currently simulates video processing (no actual video processing).
- **Presigned URLs**: Generated with the regional S3 endpoint (path-style) so uploads work without redirects and avoid `SignatureDoesNotMatch` (403).
- **ECS Code**: ECS Fargate processor code is in `processor/` and `build-and-push-docker.sh`; kept for reference, not used by the current Lambda-based pipeline.
- **Free Tier**: Architecture optimized for AWS Free Tier eligibility.
- **CORS**: S3 bucket configured with CORS for browser uploads.
- **Error Handling**: Comprehensive error handling and logging; API calls log full URLs and request details to CloudWatch.
- **Test Scripts**: Live in `scripts/`; `make test-video` exits with an error if the S3 upload fails.

## License

MIT
