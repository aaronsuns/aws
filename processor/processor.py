"""
ECS Task for video processing.

This runs as a container in ECS Fargate and processes videos from SQS messages.
It simulates video processing (transcoding, ML analysis) and updates DynamoDB.
"""
import json
import os
import sys
import time
from typing import Any, Dict

import boto3

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb")
s3_client = boto3.client("s3")

# Environment variables
JOBS_TABLE_NAME = os.getenv("JOBS_TABLE_NAME")
VIDEOS_BUCKET_NAME = os.getenv("VIDEOS_BUCKET_NAME")

if not JOBS_TABLE_NAME:
    raise RuntimeError("JOBS_TABLE_NAME environment variable is required")
if not VIDEOS_BUCKET_NAME:
    raise RuntimeError("VIDEOS_BUCKET_NAME environment variable is required")

jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def update_job_status(
    job_id: str,
    status: str,
    results: Dict[str, Any] = None,
    error: str = None,
    progress_percent: int = None,
) -> None:
    """Update job status in DynamoDB."""
    from datetime import datetime

    now = datetime.utcnow().isoformat() + "Z"

    update_expression_parts = ["SET #status = :status", "#updated_at = :updated_at"]
    expression_attribute_names = {"#status": "status", "#updated_at": "updated_at"}
    expression_attribute_values = {":status": status, ":updated_at": now}

    if results:
        update_expression_parts.append("results = :results")
        expression_attribute_values[":results"] = results

    if error:
        update_expression_parts.append("#error = :error")
        expression_attribute_names["#error"] = "error"
        expression_attribute_values[":error"] = error

    if progress_percent is not None:
        update_expression_parts.append("progress_percent = :progress")
        expression_attribute_values[":progress"] = progress_percent

    jobs_table.update_item(
        Key={"job_id": job_id},
        UpdateExpression=" ".join(update_expression_parts),
        ExpressionAttributeNames=expression_attribute_names,
        ExpressionAttributeValues=expression_attribute_values,
    )


def process_video(job_id: str, s3_bucket: str, s3_key: str) -> None:
    """
    Simulate video processing steps:
    1. Download metadata (simulated)
    2. Transcode (simulated)
    3. ML analysis (simulated)
    4. Store results
    """
    try:
        print(f"[{job_id}] Starting video processing: s3://{s3_bucket}/{s3_key}")

        # Step 1: "Download" and analyze (simulated)
        print(f"[{job_id}] Step 1: Analyzing video metadata...")
        update_job_status(job_id=job_id, status="PROCESSING", progress_percent=25)
        time.sleep(2)  # Simulate processing time

        # Get file size from S3 (real operation)
        try:
            response = s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
            file_size_bytes = response.get("ContentLength", 0)
            file_size_mb = file_size_bytes / (1024 * 1024)
        except Exception as e:
            print(f"Error getting file size: {e}")
            file_size_mb = 0

        # Step 2: "Transcode" (simulated)
        print(f"[{job_id}] Step 2: Transcoding video...")
        update_job_status(job_id=job_id, status="PROCESSING", progress_percent=50)
        time.sleep(3)

        # Step 3: "ML Analysis" (simulated - gaze tracking, object detection, etc.)
        print(f"[{job_id}] Step 3: Running ML analysis...")
        update_job_status(job_id=job_id, status="PROCESSING", progress_percent=75)
        time.sleep(2)

        # Step 4: Store results
        print(f"[{job_id}] Step 4: Storing results...")

        # Simulated results (in production, this would be real analysis data)
        results = {
            "file_size_mb": round(file_size_mb, 2),
            "duration_seconds": 120,  # Simulated
            "format": "mp4",
            "resolution": "1920x1080",  # Simulated
            "analysis": {
                "gaze_points": 1500,  # Simulated gaze tracking data
                "objects_detected": ["person", "screen", "keyboard"],
                "attention_score": 0.85,
            },
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        update_job_status(
            job_id=job_id, status="COMPLETED", results=results, progress_percent=100
        )

        print(f"[{job_id}] Processing completed successfully")

    except Exception as e:
        print(f"[{job_id}] Error during processing: {e}")
        import traceback

        traceback.print_exc()
        update_job_status(job_id=job_id, status="FAILED", error=str(e))


def main():
    """Main entry point for ECS task."""
    # Get job details from environment variables (passed by Step Functions)
    # Step Functions passes data via container overrides
    job_id = os.getenv("JOB_ID")
    s3_bucket = os.getenv("S3_BUCKET")
    s3_key = os.getenv("S3_KEY")

    if not all([job_id, s3_bucket, s3_key]):
        print("Error: Missing required environment variables")
        print(f"JOB_ID: {job_id}")
        print(f"S3_BUCKET: {s3_bucket}")
        print(f"S3_KEY: {s3_key}")
        sys.exit(1)

    print(f"Processing job: {job_id}")
    print(f"S3 location: s3://{s3_bucket}/{s3_key}")

    # Process the video
    process_video(job_id, s3_bucket, s3_key)

    print("Task completed successfully")


if __name__ == "__main__":
    main()
