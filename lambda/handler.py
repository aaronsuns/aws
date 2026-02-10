import json
import os
import sys
from typing import Any, Dict

# Lambda is a Python keyword, so we need to import the module differently
# Add the parent directory to path and import using importlib
import importlib.util
_lambda_path = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lambda_module", os.path.join(_lambda_path, "__init__.py"))
lambda_module = importlib.util.module_from_spec(spec)
sys.modules["lambda_module"] = lambda_module

# Import services using the lambda_module namespace
from services.items_service import items_service
from services.jobs_service import jobs_service


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda handler function for API Gateway HTTP API with DynamoDB CRUD operations.
    """
    # Extract request information
    request_context = event.get("requestContext", {}).get("http", {})
    http_method = request_context.get("method", "GET")
    path = request_context.get("path", "/")
    domain_name = request_context.get("domainName", "unknown")
    protocol = request_context.get("protocol", "https")
    stage = request_context.get("stage", "")
    path_parameters = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = event.get("body")
    
    # Build full URL for logging
    full_url = f"{protocol}://{domain_name}{path}"
    if query_params:
        query_string = "&".join([f"{k}={v}" for k, v in query_params.items()])
        full_url = f"{full_url}?{query_string}"
    
    # Log API endpoint call with full details
    print("=" * 80)
    print(f"API Endpoint Call: {http_method} {full_url}")
    print(f"Path: {path}")
    print(f"Domain: {domain_name}")
    print(f"Stage: {stage}")
    if path_parameters:
        print(f"Path Parameters: {json.dumps(path_parameters, indent=2)}")
    if query_params:
        print(f"Query Parameters: {json.dumps(query_params, indent=2)}")
    if body:
        try:
            body_parsed = json.loads(body) if isinstance(body, str) else body
            print(f"Request Body: {json.dumps(body_parsed, indent=2)}")
        except:
            print(f"Request Body (raw): {body[:200]}...")  # Truncate long bodies
    print("=" * 80)

    # Parse JSON body if present (after logging)
    if body:
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {"raw": body}

    # CORS headers
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

    # Handle OPTIONS request for CORS
    if http_method == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "OK"}),
        }

    try:
        # Route handling
        print(f"Routing to: {path} with method: {http_method}")
        if path == "/":
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps(
                    {
                        "message": "Welcome to AWS Serverless API with DynamoDB",
                        "database": "DynamoDB (NoSQL)",
                        "endpoints": {
                            "GET /items": "List all items",
                            "POST /items": "Create an item",
                        "GET /items/{id}": "Get item by ID",
                        "PUT /items/{id}": "Update item by ID",
                        "DELETE /items/{id}": "Delete item by ID",
                        "POST /jobs": "Create video processing job (get presigned URL)",
                        "GET /jobs/{id}": "Get job status",
                    },
                    },
                    indent=2,
                ),
            }

        elif path == "/items":
            if http_method == "GET":
                # List all items
                return list_items(headers)
            elif http_method == "POST":
                # Create new item
                return create_item(body or {}, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        elif path.startswith("/items/") and path_parameters.get("id"):
            item_id = str(path_parameters["id"])

            if http_method == "GET":
                # Get item by ID
                return get_item(item_id, headers)
            elif http_method == "PUT":
                # Update item
                return update_item(item_id, body or {}, headers)
            elif http_method == "DELETE":
                # Delete item
                return delete_item(item_id, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        elif path == "/jobs":
            if http_method == "POST":
                # Create job and get presigned URL
                return create_job(body or {}, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        elif path.startswith("/jobs/") and path_parameters.get("id"):
            job_id = str(path_parameters["id"])
            if http_method == "GET":
                # Get job status
                return get_job_status(job_id, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        else:
            return error_response(404, "Not Found", headers)

    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return error_response(500, f"Internal server error: {str(e)}", headers)


def list_items(headers: Dict[str, str]) -> Dict[str, Any]:
    """List all items via the service layer."""
    try:
        result = items_service.list_items()
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(result, indent=2),
        }
    except Exception as e:
        print(f"Error listing items: {e}")
        return error_response(500, f"Error listing items: {str(e)}", headers)


def create_item(body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """Create a new item via the service layer."""
    try:
        item = items_service.create_item(body)

        return {
            "statusCode": 201,
            "headers": headers,
            "body": json.dumps(
                {"message": "Item created", "item": item.to_dict()}, indent=2
            ),
        }
    except ValueError as ve:
        # Validation / client error
        print(f"Validation error creating item: {ve}")
        return error_response(400, str(ve), headers)
    except Exception as e:
        print(f"Error creating item: {e}")
        return error_response(500, f"Error creating item: {str(e)}", headers)


def get_item(item_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Get item by ID via the service layer."""
    try:
        item = items_service.get_item(item_id)
        if not item:
            return error_response(404, "Item not found", headers)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"item": item}, indent=2),
        }
    except Exception as e:
        print(f"Error getting item: {e}")
        return error_response(500, f"Error getting item: {str(e)}", headers)


def update_item(
    item_id: str, body: Dict[str, Any], headers: Dict[str, str]
) -> Dict[str, Any]:
    """Update item by ID via the service layer."""
    try:
        updated = items_service.update_item(item_id, body)
        if not updated:
            return error_response(404, "Item not found", headers)

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {"message": "Item updated", "item": updated.to_dict()}, indent=2
            ),
        }
    except ValueError as ve:
        print(f"Validation error updating item: {ve}")
        return error_response(400, str(ve), headers)
    except Exception as e:
        print(f"Error updating item: {e}")
        return error_response(500, f"Error updating item: {str(e)}", headers)


def delete_item(item_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Delete item by ID via the service layer."""
    try:
        deleted = items_service.delete_item(item_id)
        if not deleted:
            return error_response(404, "Item not found", headers)
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "Item deleted", "id": item_id}, indent=2),
        }
    except Exception as e:
        print(f"Error deleting item: {e}")
        return error_response(500, f"Error deleting item: {str(e)}", headers)


def create_job(body: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
    """Create a video processing job and return presigned URL."""
    try:
        if not body or "filename" not in body:
            return error_response(400, "filename is required", headers)

        filename = str(body["filename"])
        bucket_name = os.getenv("VIDEOS_BUCKET_NAME")
        if not bucket_name:
            return error_response(500, "VIDEOS_BUCKET_NAME not configured", headers)

        job, presigned_url = jobs_service.create_job(filename, bucket_name)
        
        print(f"Job created successfully: {job.job_id} for file: {filename}")
        print(f"Presigned URL: {presigned_url[:100]}...")  # Log first 100 chars of URL

        return {
            "statusCode": 201,
            "headers": headers,
            "body": json.dumps(
                {
                    "job_id": job.job_id,
                    "presigned_url": presigned_url,
                    "expires_in": 3600,
                    "status": job.status,
                    "s3_key": job.s3_key,
                },
                indent=2,
            ),
        }
    except Exception as e:
        print(f"Error creating job: {e}")
        import traceback
        traceback.print_exc()
        return error_response(500, f"Error creating job: {str(e)}", headers)


def get_job_status(job_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
    """Get job status by ID."""
    try:
        job = jobs_service.get_job(job_id)
        if not job:
            return error_response(404, "Job not found", headers)

        job_dict = job.to_dict()
        print(f"Job status retrieved successfully: {job_id} -> {job_dict.get('status', 'UNKNOWN')}")
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(job_dict, indent=2),
        }
    except Exception as e:
        print(f"Error getting job status: {e}")
        import traceback
        traceback.print_exc()
        return error_response(500, f"Error getting job status: {str(e)}", headers)


def error_response(
    status_code: int, message: str, headers: Dict[str, str]
) -> Dict[str, Any]:
    """Return error response."""
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps({"error": message}, indent=2),
    }
