"""
Lambda function triggered by SQS to start Step Functions execution.

When a video is uploaded to S3, S3 sends an event to SQS, which triggers
this Lambda. This Lambda then starts a Step Functions execution to orchestrate
the video processing workflow.
"""
import json
import os
import urllib.parse
from typing import Any, Dict

import boto3

# Initialize Step Functions client
sfn_client = boto3.client("stepfunctions")
dynamodb = boto3.resource("dynamodb")

STATE_MACHINE_ARN = os.getenv("STATE_MACHINE_ARN")
JOBS_TABLE_NAME = os.getenv("JOBS_TABLE_NAME")

if not STATE_MACHINE_ARN:
    raise RuntimeError("STATE_MACHINE_ARN environment variable is required")
if not JOBS_TABLE_NAME:
    raise RuntimeError("JOBS_TABLE_NAME environment variable is required")

jobs_table = dynamodb.Table(JOBS_TABLE_NAME)


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process SQS messages containing S3 video upload events and start Step Functions.

    Event structure (from S3 -> SQS):
    {
        "Records": [
            {
                "body": "{\"Records\":[{\"s3\":{\"bucket\":{\"name\":\"...\"},\"object\":{\"key\":\"...\"}}}]}"
            }
        ]
    }
    """
    print(f"Received event: {json.dumps(event, indent=2)}")

    # Process each SQS record
    for record in event.get("Records", []):
        try:
            # Parse SQS message body (contains S3 event)
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
                s3_key_encoded = s3_info.get("object", {}).get("key", "")
                s3_key = urllib.parse.unquote_plus(s3_key_encoded)

                if not s3_bucket or not s3_key:
                    print(f"Invalid S3 event: {s3_record}")
                    continue

                print(f"Processing S3 event: s3://{s3_bucket}/{s3_key}")

                # Extract job_id from S3 key (format: uploads/{job_id}/{filename})
                parts = s3_key.split("/")
                if len(parts) >= 2 and parts[0] == "uploads":
                    job_id = parts[1]
                else:
                    print(f"ERROR: Could not extract job_id from S3 key: {s3_key}")
                    print(f"Expected format: uploads/{{job_id}}/{{filename}}, got: {s3_key}")
                    continue
                
                # Verify job exists in DynamoDB
                try:
                    job_response = jobs_table.get_item(Key={"job_id": job_id})
                    if "Item" not in job_response:
                        print(f"WARNING: Job {job_id} not found in DynamoDB, but file exists in S3: {s3_key}")
                        # Continue anyway - might be a race condition
                    else:
                        current_status = job_response["Item"].get("status", {}).get("S", "UNKNOWN")
                        print(f"Job {job_id} found in DynamoDB with status: {current_status}")
                except Exception as e:
                    print(f"ERROR: Failed to check job in DynamoDB: {e}")
                    # Continue anyway - will update status below

                # Update job status to PROCESSING
                from datetime import datetime

                now = datetime.utcnow().isoformat() + "Z"
                jobs_table.update_item(
                    Key={"job_id": job_id},
                    UpdateExpression="SET #status = :status, #updated_at = :updated_at",
                    ExpressionAttributeNames={"#status": "status", "#updated_at": "updated_at"},
                    ExpressionAttributeValues={":status": "PROCESSING", ":updated_at": now},
                )

                # Start Step Functions execution
                execution_input = {
                    "job_id": job_id,
                    "s3_bucket": s3_bucket,
                    "s3_key": s3_key,
                }

                execution_name = f"video-processing-{job_id}"

                response = sfn_client.start_execution(
                    stateMachineArn=STATE_MACHINE_ARN,
                    name=execution_name,
                    input=json.dumps(execution_input),
                )

                print(
                    f"Started Step Functions execution: {response['executionArn']} for job {job_id}"
                )

        except Exception as e:
            print(f"Error processing record: {e}")
            import traceback

            traceback.print_exc()
            # In production, you might want to send to DLQ
            continue

    return {"statusCode": 200, "body": "Step Functions executions started"}
