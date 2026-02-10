"""Unit tests for jobs_service (DynamoDB conversion and Job model)."""
import pytest
from decimal import Decimal

from services.jobs_service import (
    Job,
    convert_dynamodb_item,
    convert_dynamodb_value,
)


class TestConvertDynamodbValue:
    """Tests for convert_dynamodb_value."""

    def test_decimal_int(self):
        assert convert_dynamodb_value(Decimal("42")) == 42

    def test_decimal_float(self):
        assert convert_dynamodb_value(Decimal("3.14")) == 3.14

    def test_string_passthrough(self):
        assert convert_dynamodb_value("hello") == "hello"

    def test_none_passthrough(self):
        assert convert_dynamodb_value(None) is None

    def test_dynamodb_string_type(self):
        assert convert_dynamodb_value({"S": "foo"}) == "foo"

    def test_dynamodb_number_type_int(self):
        assert convert_dynamodb_value({"N": "100"}) == 100

    def test_dynamodb_number_type_float(self):
        assert convert_dynamodb_value({"N": "1.5"}) == 1.5

    def test_dynamodb_null_type(self):
        assert convert_dynamodb_value({"NULL": True}) is None

    def test_dynamodb_list_type(self):
        result = convert_dynamodb_value({"L": [{"S": "a"}, {"N": "1"}]})
        assert result == ["a", 1]

    def test_dynamodb_map_type(self):
        result = convert_dynamodb_value({"M": {"name": {"S": "test"}, "count": {"N": "2"}}})
        assert result == {"name": "test", "count": 2}


class TestConvertDynamodbItem:
    """Tests for convert_dynamodb_item."""

    def test_empty_item(self):
        assert convert_dynamodb_item({}) == {}

    def test_item_with_decimal(self):
        raw = {"job_id": "j1", "progress_percent": Decimal("100"), "status": "COMPLETED"}
        result = convert_dynamodb_item(raw)
        assert result == {"job_id": "j1", "progress_percent": 100, "status": "COMPLETED"}

    def test_item_with_nested_dict(self):
        raw = {
            "job_id": "j1",
            "results": {"duration_seconds": Decimal("120"), "nested": {"score": Decimal("0")}},
        }
        result = convert_dynamodb_item(raw)
        assert result["job_id"] == "j1"
        assert result["results"]["duration_seconds"] == 120
        assert result["results"]["nested"]["score"] == 0


class TestJob:
    """Tests for Job dataclass and from_dict/to_dict."""

    def test_from_dict_minimal(self):
        job = Job.from_dict({"job_id": "id1", "status": "PENDING"})
        assert job.job_id == "id1"
        assert job.status == "PENDING"
        assert job.filename is None

    def test_from_dict_full(self):
        data = {
            "job_id": "id1",
            "status": "COMPLETED",
            "filename": "v.mp4",
            "s3_key": "uploads/id1/v.mp4",
            "s3_bucket": "bucket",
            "progress_percent": 100,
        }
        job = Job.from_dict(data)
        assert job.job_id == "id1"
        assert job.status == "COMPLETED"
        assert job.filename == "v.mp4"
        assert job.s3_key == "uploads/id1/v.mp4"
        assert job.progress_percent == 100

    def test_to_dict(self):
        job = Job(
            job_id="id1",
            status="PENDING",
            filename="v.mp4",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-01T00:00:00Z",
        )
        d = job.to_dict()
        assert d["job_id"] == "id1"
        assert d["status"] == "PENDING"
        assert d["filename"] == "v.mp4"
        assert "created_at" in d
        assert "updated_at" in d

    def test_to_dict_roundtrip(self):
        data = {"job_id": "id1", "status": "COMPLETED", "filename": "v.mp4"}
        job = Job.from_dict(data)
        out = job.to_dict()
        assert out["job_id"] == data["job_id"]
        assert out["status"] == data["status"]
        assert out["filename"] == data["filename"]
