import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from datetime import datetime
import uuid

# Initialize DynamoDB client (reused across invocations)
dynamodb = boto3.resource("dynamodb")
table_name = os.environ.get("ITEMS_TABLE_NAME")
table = dynamodb.Table(table_name) if table_name else None


def lambda_handler(event, context):
    """
    AWS Lambda handler function for API Gateway HTTP API with DynamoDB CRUD operations.
    """
    # Extract request information
    http_method = event.get("requestContext", {}).get("http", {}).get("method", "GET")
    path = event.get("requestContext", {}).get("http", {}).get("path", "/")
    path_parameters = event.get("pathParameters") or {}
    query_params = event.get("queryStringParameters") or {}
    body = event.get("body")

    # Parse JSON body if present
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
                return create_item(body, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        elif path.startswith("/items/") and path_parameters.get("id"):
            item_id = path_parameters["id"]

            if http_method == "GET":
                # Get item by ID
                return get_item(item_id, headers)
            elif http_method == "PUT":
                # Update item
                return update_item(item_id, body, headers)
            elif http_method == "DELETE":
                # Delete item
                return delete_item(item_id, headers)
            else:
                return error_response(405, "Method not allowed", headers)

        else:
            return error_response(404, "Not Found", headers)

    except Exception as e:
        print(f"Error processing request: {e}")
        import traceback
        traceback.print_exc()
        return error_response(500, f"Internal server error: {str(e)}", headers)


def list_items(headers):
    """List all items."""
    try:
        # Scan table to get all items
        response = table.scan()
        items = response.get("Items", [])

        # Convert DynamoDB items to standard format
        formatted_items = [
            {
                "id": item.get("id"),
                "name": item.get("name", ""),
                "description": item.get("description", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
            }
            for item in items
        ]

        # Sort by created_at (most recent first)
        formatted_items.sort(
            key=lambda x: x.get("created_at", ""), reverse=True
        )

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {"items": formatted_items, "count": len(formatted_items)}, indent=2
            ),
        }
    except Exception as e:
        print(f"Error listing items: {e}")
        return error_response(500, f"Error listing items: {str(e)}", headers)


def create_item(body, headers):
    """Create a new item."""
    if not body or "name" not in body:
        return error_response(400, "Name is required", headers)

    try:
        item_id = str(uuid.uuid4())
        name = body.get("name")
        description = body.get("description", "")
        now = datetime.utcnow().isoformat() + "Z"

        item = {
            "id": item_id,
            "name": name,
            "description": description,
            "created_at": now,
            "updated_at": now,
        }

        table.put_item(Item=item)

        return {
            "statusCode": 201,
            "headers": headers,
            "body": json.dumps({"message": "Item created", "item": item}, indent=2),
        }
    except Exception as e:
        print(f"Error creating item: {e}")
        return error_response(500, f"Error creating item: {str(e)}", headers)


def get_item(item_id, headers):
    """Get item by ID."""
    try:
        response = table.get_item(Key={"id": item_id})

        if "Item" not in response:
            return error_response(404, "Item not found", headers)

        item = response["Item"]

        formatted_item = {
            "id": item.get("id"),
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"item": formatted_item}, indent=2),
        }
    except Exception as e:
        print(f"Error getting item: {e}")
        return error_response(500, f"Error getting item: {str(e)}", headers)


def update_item(item_id, body, headers):
    """Update item by ID."""
    if not body:
        return error_response(400, "Request body is required", headers)

    try:
        # Check if item exists
        response = table.get_item(Key={"id": item_id})
        if "Item" not in response:
            return error_response(404, "Item not found", headers)

        # Build update expression
        update_expression_parts = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        if "name" in body:
            update_expression_parts.append("#name = :name")
            expression_attribute_names["#name"] = "name"
            expression_attribute_values[":name"] = body["name"]

        if "description" in body:
            update_expression_parts.append("#description = :description")
            expression_attribute_names["#description"] = "description"
            expression_attribute_values[":description"] = body["description"]

        if not update_expression_parts:
            return error_response(400, "No fields to update", headers)

        # Always update updated_at
        update_expression_parts.append("#updated_at = :updated_at")
        expression_attribute_names["#updated_at"] = "updated_at"
        expression_attribute_values[":updated_at"] = datetime.utcnow().isoformat() + "Z"

        update_expression = "SET " + ", ".join(update_expression_parts)

        # Update item
        table.update_item(
            Key={"id": item_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values,
            ReturnValues="ALL_NEW",
        )

        # Get updated item
        response = table.get_item(Key={"id": item_id})
        item = response["Item"]

        formatted_item = {
            "id": item.get("id"),
            "name": item.get("name", ""),
            "description": item.get("description", ""),
            "created_at": item.get("created_at", ""),
            "updated_at": item.get("updated_at", ""),
        }

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps(
                {"message": "Item updated", "item": formatted_item}, indent=2
            ),
        }
    except Exception as e:
        print(f"Error updating item: {e}")
        return error_response(500, f"Error updating item: {str(e)}", headers)


def delete_item(item_id, headers):
    """Delete item by ID."""
    try:
        # Check if item exists
        response = table.get_item(Key={"id": item_id})
        if "Item" not in response:
            return error_response(404, "Item not found", headers)

        # Delete item
        table.delete_item(Key={"id": item_id})

        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({"message": "Item deleted", "id": item_id}, indent=2),
        }
    except Exception as e:
        print(f"Error deleting item: {e}")
        return error_response(500, f"Error deleting item: {str(e)}", headers)


def error_response(status_code, message, headers):
    """Return error response."""
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps({"error": message}, indent=2),
    }
