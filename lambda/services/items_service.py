from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

from repositories.items_repository import ItemsRepository


@dataclass
class Item:
    id: str
    name: str
    description: str
    created_at: str
    updated_at: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Item":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at", ""),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class ItemsService:
    """Domain-level operations for items.

    This layer contains business rules and orchestrates calls to the
    underlying repository. It deliberately does not know anything about
    API Gateway events or HTTP; the handler is responsible for that.
    """

    def __init__(self, repository: ItemsRepository) -> None:
        self._repository = repository

    # Query operations
    def list_items(self) -> Dict[str, Any]:
        raw_items = self._repository.list_items()
        items = [Item.from_dict(i) for i in raw_items]

        # Sort by created_at (most recent first). This keeps existing behaviour
        # but could be replaced with a more scalable query design later.
        items.sort(key=lambda x: x.created_at or "", reverse=True)

        return {
            "items": [i.to_dict() for i in items],
            "count": len(items),
        }

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        raw = self._repository.get_item(item_id)
        if not raw:
            return None
        return Item.from_dict(raw).to_dict()

    # Mutation operations
    def create_item(self, body: Dict[str, Any]) -> Item:
        if not body or "name" not in body:
            raise ValueError("Name is required")

        now = datetime.utcnow().isoformat() + "Z"
        item = Item(
            id=str(uuid.uuid4()),
            name=str(body.get("name", "")),
            description=str(body.get("description", "")),
            created_at=now,
            updated_at=now,
        )

        self._repository.put_item(item.to_dict())
        return item

    def update_item(self, item_id: str, body: Dict[str, Any]) -> Optional[Item]:
        if not body:
            raise ValueError("Request body is required")

        existing_raw = self._repository.get_item(item_id)
        if not existing_raw:
            return None

        existing = Item.from_dict(existing_raw)

        if "name" in body:
            existing.name = str(body["name"])
        if "description" in body:
            existing.description = str(body["description"])

        existing.updated_at = datetime.utcnow().isoformat() + "Z"
        self._repository.put_item(existing.to_dict())
        return existing

    def delete_item(self, item_id: str) -> bool:
        return self._repository.delete_item(item_id)


# Module-level singleton used by the Lambda handler.
items_service = ItemsService(ItemsRepository())

