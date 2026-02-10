"""Unit tests for items_service (Item model)."""
import pytest

from services.items_service import Item


class TestItem:
    """Tests for Item dataclass and from_dict/to_dict."""

    def test_from_dict_minimal(self):
        item = Item.from_dict({"id": "i1"})
        assert item.id == "i1"
        assert item.name == ""
        assert item.description == ""

    def test_from_dict_full(self):
        data = {
            "id": "i1",
            "name": "Test",
            "description": "Desc",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        item = Item.from_dict(data)
        assert item.id == data["id"]
        assert item.name == data["name"]
        assert item.description == data["description"]

    def test_to_dict(self):
        item = Item(
            id="i1",
            name="N",
            description="D",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        d = item.to_dict()
        assert d["id"] == "i1"
        assert d["name"] == "N"
        assert d["description"] == "D"

    def test_to_dict_roundtrip(self):
        data = {
            "id": "i1",
            "name": "Test",
            "description": "Desc",
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-01T00:00:00Z",
        }
        item = Item.from_dict(data)
        out = item.to_dict()
        assert out == data
