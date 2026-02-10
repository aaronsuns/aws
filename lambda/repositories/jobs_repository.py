import os
from typing import Any, Dict, Optional

import boto3


_dynamodb = boto3.resource("dynamodb")
_table_name = os.getenv("JOBS_TABLE_NAME")

if not _dynamodb:
    raise RuntimeError("DynamoDB resource could not be initialised")

if not _table_name:
    raise RuntimeError("JOBS_TABLE_NAME environment variable is required")

_table = _dynamodb.Table(_table_name)


class JobsRepository:
    """Data access layer for video processing jobs stored in DynamoDB."""

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a job by ID."""
        response = _table.get_item(Key={"job_id": job_id})
        return response.get("Item")

    def put_job(self, job: Dict[str, Any]) -> None:
        """Create or update a job."""
        _table.put_item(Item=job)

    def update_job_status(
        self, job_id: str, status: str, **kwargs: Any
    ) -> None:
        """Update job status and optionally other fields."""
        update_expression_parts = ["SET #status = :status"]
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {":status": status}

        if "updated_at" in kwargs:
            update_expression_parts.append(", #updated_at = :updated_at")
            expression_attribute_names["#updated_at"] = "updated_at"
            expression_attribute_values[":updated_at"] = kwargs["updated_at"]

        if "results" in kwargs:
            update_expression_parts.append(", results = :results")
            expression_attribute_values[":results"] = kwargs["results"]

        if "error" in kwargs:
            update_expression_parts.append(", #error = :error")
            expression_attribute_names["#error"] = "error"
            expression_attribute_values[":error"] = kwargs["error"]

        if "progress_percent" in kwargs:
            update_expression_parts.append(", progress_percent = :progress")
            expression_attribute_values[":progress"] = kwargs["progress_percent"]

        _table.update_item(
            Key={"job_id": job_id},
            UpdateExpression=" ".join(update_expression_parts),
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
        )
