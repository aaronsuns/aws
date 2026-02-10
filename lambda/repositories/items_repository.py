import os
from typing import Any, Dict, List

import boto3


_dynamodb = boto3.resource("dynamodb")
_table_name = os.getenv("ITEMS_TABLE_NAME")

if not _dynamodb:
    # This should never happen in Lambda, but keeps mypy and type checkers happy.
    raise RuntimeError("DynamoDB resource could not be initialised")

if not _table_name:
    # Fail fast during cold start if the environment is misconfigured.
    raise RuntimeError("ITEMS_TABLE_NAME environment variable is required")

_table = _dynamodb.Table(_table_name)


class ItemsRepository:
    """Data access layer for items stored in DynamoDB.

    This class encapsulates all direct interaction with DynamoDB so that the
    rest of the codebase does not depend on boto3 primitives. It also makes
    it easier to test the domain logic by swapping this implementation with
    an in-memory or stubbed repository in unit tests.
    """

    def list_items(self) -> List[Dict[str, Any]]:
        """Return all items.

        NOTE: This implementation uses a full table scan, which is fine for
        small demo datasets but should be replaced with a paginated Query
        design for production-scale workloads.
        """
        response = _table.scan()
        return response.get("Items", [])

    def get_item(self, item_id: str) -> Dict[str, Any] | None:
        response = _table.get_item(Key={"id": item_id})
        return response.get("Item")

    def put_item(self, item: Dict[str, Any]) -> None:
        _table.put_item(Item=item)

    def delete_item(self, item_id: str) -> bool:
        # We first check existence so that callers can return a 404 if needed.
        existing = self.get_item(item_id)
        if not existing:
            return False

        _table.delete_item(Key={"id": item_id})
        return True
