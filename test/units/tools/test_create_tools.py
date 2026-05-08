"""Unit tests for create tools layer."""
import json

import pytest
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio


def _get_fn(tool):
    """Extract the underlying async function from a FastMCP FunctionTool."""
    return tool.fn


def _unwrap(result):
    """Unwrap tool result — handles both str and dict returns."""
    if isinstance(result, dict):
        return result.get("result", str(result))
    return result


@pytest.fixture
def mock_mongodb_service():
    """Patch mongodb_service at tools layer."""
    with patch("mongodb_mcp.tools.mongodb.mongodb_service") as mock_svc:
        yield mock_svc


class TestInsertOneTool:
    async def test_inserts_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        mock_mongodb_service.insert_one = AsyncMock(return_value={
            "status": "ok",
            "inserted_id": "abc123",
        })

        raw = await _get_fn(insert_one)("mydb", "users", '{"name": "Alice"}')

        assert "Inserted 1 document" in _unwrap(raw)
        assert "abc123" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_invalid_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        raw = await _get_fn(insert_one)("mydb", "users", "not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        mock_mongodb_service.insert_one = AsyncMock(return_value={
            "status": "error",
            "message": "Document must be a non-empty JSON object.",
        })

        raw = await _get_fn(insert_one)("mydb", "users", '{}')

        assert "Error" in _unwrap(raw)
        assert "non-empty" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        mock_mongodb_service.insert_one = AsyncMock(
            side_effect=PermissionError("read-only mode")
        )

        raw = await _get_fn(insert_one)("mydb", "users", '{"a": 1}')

        assert "Error" in _unwrap(raw)
        assert "read-only" in _unwrap(raw)


class TestInsertManyTool:
    async def test_inserts_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        mock_mongodb_service.insert_many = AsyncMock(return_value={
            "status": "ok",
            "inserted_count": 3,
            "inserted_ids": ["id1", "id2", "id3"],
        })

        docs = json.dumps([{"a": 1}, {"b": 2}, {"c": 3}])
        raw = await _get_fn(insert_many)("mydb", "users", docs)

        assert "Inserted 3 documents" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_invalid_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        raw = await _get_fn(insert_many)("mydb", "users", "{bad")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_rejects_non_array(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        raw = await _get_fn(insert_many)("mydb", "users", '{"a": 1}')

        assert "Error" in _unwrap(raw)
        assert "JSON array" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        mock_mongodb_service.insert_many = AsyncMock(return_value={
            "status": "error",
            "message": "Item at index 1 is not a JSON object.",
        })

        docs = json.dumps([{"ok": 1}, "bad"])
        raw = await _get_fn(insert_many)("mydb", "users", docs)

        assert "Error" in _unwrap(raw)
        assert "index 1" in _unwrap(raw)


class TestCreateCollectionTool:
    async def test_creates_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collection": "products",
        })

        raw = await _get_fn(create_collection)("mydb", "products")

        assert "products" in _unwrap(raw)
        assert "created" in _unwrap(raw)
        assert "mydb" in _unwrap(raw)

    async def test_already_exists(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(return_value={
            "status": "error",
            "message": "Collection 'users' already exists in database 'mydb'.",
        })

        raw = await _get_fn(create_collection)("mydb", "users")

        assert "Error" in _unwrap(raw)
        assert "already exists" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(
            side_effect=PermissionError("read-only mode")
        )

        raw = await _get_fn(create_collection)("mydb", "new_col")

        assert "Error" in _unwrap(raw)
        assert "read-only" in _unwrap(raw)


class TestCreateIndexTool:
    async def test_creates_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        mock_mongodb_service.create_index = AsyncMock(return_value={
            "status": "ok",
            "index_name": "name_1_age_-1",
            "database": "mydb",
            "collection": "users",
        })

        keys = json.dumps([["name", 1], ["age", -1]])
        raw = await _get_fn(create_index)("mydb", "users", keys)

        assert "name_1_age_-1" in _unwrap(raw)
        assert "created" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_invalid_json_keys(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        raw = await _get_fn(create_index)("mydb", "users", "not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_keys_not_array(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        raw = await _get_fn(create_index)("mydb", "users", '{"field": 1}')

        assert "Error" in _unwrap(raw)
        assert "JSON array" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        mock_mongodb_service.create_index = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        keys = json.dumps([["name", 1]])
        raw = await _get_fn(create_index)("mydb", "uesrs", keys)

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)
        assert "users" in _unwrap(raw)
