import json


def lambda_handler(event, context):
    """
    AWS Lambda handler function for API Gateway HTTP API.
    
    Args:
        event: API Gateway HTTP API event
        context: Lambda context object
    
    Returns:
        API Gateway HTTP API response
    """
    
    # Extract request information
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("requestContext", {}).get("http", {}).get("path", "/")
    query_params = event.get("queryStringParameters") or {}
    body = event.get("body")
    
    # Parse JSON body if present
    if body:
        try:
            body = json.loads(body)
        except json.JSONDecodeError:
            body = {"raw": body}
    
    # Handle different routes
    if path == "/hello":
        response_data = {
            "message": "Hello from AWS Lambda!",
            "method": http_method,
            "path": path,
            "query_params": query_params,
            "body": body,
        }
    elif path == "/":
        response_data = {
            "message": "Welcome to AWS Serverless API",
            "method": http_method,
            "path": path,
            "status": "success",
        }
    else:
        response_data = {
            "message": "Not Found",
            "path": path,
            "status": "error",
        }
    
    # Return API Gateway HTTP API response format
    return {
        "statusCode": 200 if path != "/" or path == "/hello" else 404,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # Adjust CORS as needed
        },
        "body": json.dumps(response_data, indent=2),
    }
