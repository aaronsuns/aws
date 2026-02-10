"""Pytest configuration and fixtures."""
import os
import sys

# Ensure lambda package is on path (lambda is a reserved name so we add the dir)
_lambda_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lambda")
if _lambda_dir not in sys.path:
    sys.path.insert(0, _lambda_dir)

# Avoid DynamoDB/S3 init in repos when importing services in tests
os.environ.setdefault("JOBS_TABLE_NAME", "test-jobs-table")
os.environ.setdefault("ITEMS_TABLE_NAME", "test-items-table")
os.environ.setdefault("AWS_REGION", "eu-north-1")
