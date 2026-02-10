"""Pytest configuration and fixtures."""
import os
import sys

# Ensure lambda package is on path (lambda is a reserved name so we add the dir)
_lambda_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambda")
if _lambda_dir not in sys.path:
    sys.path.insert(0, _lambda_dir)

# Set before any lambda imports so boto3 has a region at import time (CI has no AWS config)
os.environ.setdefault("JOBS_TABLE_NAME", "test-jobs-table")
os.environ.setdefault("ITEMS_TABLE_NAME", "test-items-table")
if not os.environ.get("AWS_REGION") and not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_REGION"] = "us-east-1"
