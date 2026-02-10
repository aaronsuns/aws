"""
Lambda function triggered by SQS to process video uploads.

This simulates video processing (transcoding, ML analysis, etc.) without
actually processing video files. In production, this would run in ECS
or use GPU-enabled Lambda for real video processing.
"""
import json
import os
import time
import urllib.parse
from typing import Any, Dict

import boto3

from services.jobs_service import jobs_service

# Initialize S3 client
_s3_client = boto3.client("s3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process video from Step Functions invocation or SQS event.
    
    Step Functions invocation (preferred):
    {
        "job_id": "uuid",
        "s3_bucket": "bucket-name",
        "s3_key": "uploads/uuid/video.mp4"
    }
    
    SQS event (legacy, kept for compatibility):
    {
        "Records": [{"body": "{\"Records\":[{\"s3\":{...}}]}"}]
    }
    """
    print(f"Received event: {json.dumps(event, indent=2)}")

    bucket_name = os.getenv("VIDEOS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("VIDEOS_BUCKET_NAME environment variable is required")

    # Check if this is a Step Functions invocation (direct event with job_id)
    if "job_id" in event and "s3_bucket" in event and "s3_key" in event:
        # Step Functions invocation
        job_id = event["job_id"]
        s3_bucket = event["s3_bucket"]
        s3_key = event["s3_key"]
        
        print(f"Processing video from Step Functions: s3://{s3_bucket}/{s3_key}")
        
        # Update job status to PROCESSING
        jobs_service.update_job_status(
            job_id=job_id,
            status="PROCESSING",
            progress_percent=0,
        )
        
        # Simulate video processing steps
        simulate_processing(job_id, s3_bucket, s3_key)
        
        return {
            "statusCode": 200,
            "job_id": job_id,
            "status": "COMPLETED",
        }
    
    # Legacy: Handle SQS event (for backward compatibility)
    # Process each SQS record
    for record in event.get("Records", []):
        try:
            # S3 sends events to SQS, and the message body contains the S3 event JSON
            # The body might be a string that needs parsing
            body = record.get("body", "{}")
            if isinstance(body, str):
                sqs_body = json.loads(body)
            else:
                sqs_body = body

            # S3 event structure: {"Records": [{"s3": {...}}]}
            s3_records = sqs_body.get("Records", [])

            for s3_record in s3_records:
                s3_info = s3_record.get("s3", {})
                s3_bucket = s3_info.get("bucket", {}).get("name")
                # S3 key is URL-encoded, decode it
                s3_key_encoded = s3_info.get("object", {}).get("key", "")
                s3_key = urllib.parse.unquote_plus(s3_key_encoded)

                if not s3_bucket or not s3_key:
                    print(f"Invalid S3 event: {s3_record}")
                    continue

                print(f"Processing video: s3://{s3_bucket}/{s3_key}")

                # Extract job_id from S3 key (format: uploads/{job_id}/{filename})
                # Example: uploads/550e8400-e29b-41d4-a716-446655440000/video.mp4
                parts = s3_key.split("/")
                if len(parts) >= 2 and parts[0] == "uploads":
                    job_id = parts[1]
                else:
                    # Fallback: try to find job by s3_key
                    print(f"Could not extract job_id from key: {s3_key}")
                    continue

                # Update job status to PROCESSING
                jobs_service.update_job_status(
                    job_id=job_id,
                    status="PROCESSING",
                    progress_percent=0,
                )

                # Simulate video processing steps
                simulate_processing(job_id, s3_bucket, s3_key)

        except Exception as e:
            print(f"Error processing record: {e}")
            import traceback
            traceback.print_exc()
            # In production, you might want to send to DLQ or update job status to FAILED
            continue

    return {"statusCode": 200, "body": "Processing completed"}


def simulate_processing(job_id: str, bucket_name: str, s3_key: str) -> None:
    """
    Simulate video processing steps:
    1. Download metadata (simulated)
    2. Transcode (simulated)
    3. ML analysis (simulated)
    4. Store results
    """
    try:
        # Step 1: "Download" and analyze (simulated)
        print(f"[{job_id}] Step 1: Analyzing video metadata...")
        jobs_service.update_job_status(
            job_id=job_id,
            status="PROCESSING",
            progress_percent=25,
        )
        time.sleep(1)  # Simulate processing time

        # Get file size from S3 (real operation)
        try:
            response = _s3_client.head_object(Bucket=bucket_name, Key=s3_key)
            file_size_bytes = response.get("ContentLength", 0)
            file_size_mb = file_size_bytes / (1024 * 1024)
        except Exception as e:
            print(f"Error getting file size: {e}")
            file_size_mb = 0

        # Step 2: "Transcode" (simulated)
        print(f"[{job_id}] Step 2: Transcoding video...")
        jobs_service.update_job_status(
            job_id=job_id,
            status="PROCESSING",
            progress_percent=50,
        )
        time.sleep(1)

        # Step 3: "ML Analysis" (simulated - gaze tracking, object detection, etc.)
        print(f"[{job_id}] Step 3: Running ML analysis...")
        jobs_service.update_job_status(
            job_id=job_id,
            status="PROCESSING",
            progress_percent=75,
        )
        time.sleep(1)

        # Step 4: Store results
        print(f"[{job_id}] Step 4: Storing results...")
        
        # Simulated results (in production, this would be real analysis data)
        # DynamoDB doesn't support float, so convert to string or use Decimal
        from decimal import Decimal
        results = {
            "file_size_mb": str(round(file_size_mb, 2)),  # Convert to string for DynamoDB
            "duration_seconds": 120,  # Simulated
            "format": "mp4",
            "resolution": "1920x1080",  # Simulated
            "analysis": {
                "gaze_points": 1500,  # Simulated gaze tracking data
                "objects_detected": ["person", "screen", "keyboard"],
                "attention_score": "0.85",  # Convert to string for DynamoDB
            },
            "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        jobs_service.update_job_status(
            job_id=job_id,
            status="COMPLETED",
            results=results,
            progress_percent=100,
        )

        print(f"[{job_id}] Processing completed successfully")

    except Exception as e:
        print(f"[{job_id}] Error during processing: {e}")
        import traceback
        traceback.print_exc()
        jobs_service.update_job_status(
            job_id=job_id,
            status="FAILED",
            error=str(e),
        )
