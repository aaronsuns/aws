from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional
import uuid

import boto3

from repositories.jobs_repository import JobsRepository


def convert_dynamodb_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB item to regular Python dict, handling Decimal types.
    
    boto3 resource returns Decimal objects for numbers, which aren't JSON serializable.
    This function recursively converts all Decimal values to int or float.
    """
    if not item:
        return item
    
    result = {}
    for key, value in item.items():
        result[key] = convert_dynamodb_value(value)
    
    return result


def convert_dynamodb_value(value: Any) -> Any:
    """Convert a single DynamoDB value to Python type, handling Decimal and nested structures."""
    if isinstance(value, Decimal):
        # Convert Decimal to int if it's a whole number, otherwise float
        if value % 1 == 0:
            return int(value)
        return float(value)
    elif isinstance(value, dict):
        # Handle nested dicts (like results field)
        # Check if it's a DynamoDB attribute type (boto3 client format)
        if "M" in value:  # DynamoDB Map type
            return convert_dynamodb_item(value["M"])
        elif "L" in value:  # DynamoDB List type
            return [convert_dynamodb_value(v) for v in value["L"]]
        elif "S" in value:  # String
            return value["S"]
        elif "N" in value:  # Number
            num_str = value["N"]
            try:
                if "." in num_str:
                    return float(num_str)
                return int(num_str)
            except ValueError:
                return float(num_str)
        elif "BOOL" in value:  # Boolean
            return value["BOOL"]
        elif "NULL" in value:  # Null
            return None
        else:
            # Regular dict - recurse to handle nested Decimal values
            return convert_dynamodb_item(value)
    elif isinstance(value, list):
        return [convert_dynamodb_value(v) for v in value]
    elif isinstance(value, (str, int, float, bool, type(None))):
        return value
    else:
        # Unknown type - return as is
        return value


@dataclass
class Job:
    job_id: str
    status: str  # PENDING, PROCESSING, COMPLETED, FAILED
    s3_key: Optional[str] = None
    s3_bucket: Optional[str] = None
    filename: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    progress_percent: Optional[int] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Job":
        return cls(
            job_id=data.get("job_id", ""),
            status=data.get("status", "PENDING"),
            s3_key=data.get("s3_key"),
            s3_bucket=data.get("s3_bucket"),
            filename=data.get("filename"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            results=data.get("results"),
            error=data.get("error"),
            progress_percent=data.get("progress_percent"),
        )

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "job_id": self.job_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if self.s3_key:
            result["s3_key"] = self.s3_key
        if self.s3_bucket:
            result["s3_bucket"] = self.s3_bucket
        if self.filename:
            result["filename"] = self.filename
        if self.results:
            result["results"] = self.results
        if self.error:
            result["error"] = self.error
        if self.progress_percent is not None:
            result["progress_percent"] = self.progress_percent
        return result


class JobsService:
    """Domain-level operations for video processing jobs."""

    def __init__(self, repository: JobsRepository) -> None:
        self._repository = repository
        self._s3_client = boto3.client("s3")

    def create_job(self, filename: str, bucket_name: str) -> tuple[Job, str]:
        """Create a new job and generate presigned URL for upload.

        Returns:
            Tuple of (Job, presigned_url)
        """
        job_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat() + "Z"
        
        # Generate S3 key (simulate user folder structure)
        s3_key = f"uploads/{job_id}/{filename}"

        # Create job record
        job = Job(
            job_id=job_id,
            status="PENDING",
            s3_key=s3_key,
            s3_bucket=bucket_name,
            filename=filename,
            created_at=now,
            updated_at=now,
        )

        self._repository.put_job(job.to_dict())

        # Generate presigned URL for PUT (expires in 1 hour)
        # Don't include ContentType in params to avoid CORS preflight issues
        # The browser will set Content-Type header, and S3 CORS will allow it
        presigned_url = self._s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": bucket_name,
                "Key": s3_key,
            },
            ExpiresIn=3600,  # 1 hour
        )

        return job, presigned_url

    def get_job(self, job_id: str) -> Optional[Job]:
        """Get job by ID."""
        raw = self._repository.get_job(job_id)
        if not raw:
            return None
        # Convert DynamoDB types (Decimal, etc.) to Python types
        converted = convert_dynamodb_item(raw)
        return Job.from_dict(converted)

    def update_job_status(
        self,
        job_id: str,
        status: str,
        results: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        progress_percent: Optional[int] = None,
    ) -> None:
        """Update job status."""
        now = datetime.utcnow().isoformat() + "Z"
        self._repository.update_job_status(
            job_id=job_id,
            status=status,
            updated_at=now,
            results=results,
            error=error,
            progress_percent=progress_percent,
        )


# Module-level singleton
jobs_service = JobsService(JobsRepository())
