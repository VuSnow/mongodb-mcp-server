"""Unit tests for create tools layer."""
import json

import pytest
from unittest.mock import AsyncMock, patch


pytestmark = pytest.mark.asyncio


def _get_fn(tool):
    """Extract the underlying async function from a FastMCP FunctionTool."""
    return tool.fn


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

        result = await _get_fn(insert_one)("mydb", "users", '{"name": "Alice"}')

        assert "Inserted 1 document" in result
        assert "abc123" in result
        assert "mydb.users" in result

    async def test_invalid_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        result = await _get_fn(insert_one)("mydb", "users", "not json")

        assert "Error" in result
        assert "valid JSON" in result

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        mock_mongodb_service.insert_one = AsyncMock(return_value={
            "status": "error",
            "message": "Document must be a non-empty JSON object.",
        })

        result = await _get_fn(insert_one)("mydb", "users", '{}')

        assert "Error" in result
        assert "non-empty" in result

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_one

        mock_mongodb_service.insert_one = AsyncMock(
            side_effect=PermissionError("read-only mode")
        )

        result = await _get_fn(insert_one)("mydb", "users", '{"a": 1}')

        assert "Error" in result
        assert "read-only" in result


class TestInsertManyTool:
    async def test_inserts_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        mock_mongodb_service.insert_many = AsyncMock(return_value={
            "status": "ok",
            "inserted_count": 3,
            "inserted_ids": ["id1", "id2", "id3"],
        })

        docs = json.dumps([{"a": 1}, {"b": 2}, {"c": 3}])
        result = await _get_fn(insert_many)("mydb", "users", docs)

        assert "Inserted 3 documents" in result
        assert "mydb.users" in result

    async def test_invalid_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        result = await _get_fn(insert_many)("mydb", "users", "{bad")

        assert "Error" in result
        assert "valid JSON" in result

    async def test_rejects_non_array(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        result = await _get_fn(insert_many)("mydb", "users", '{"a": 1}')

        assert "Error" in result
        assert "JSON array" in result

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import insert_many

        mock_mongodb_service.insert_many = AsyncMock(return_value={
            "status": "error",
            "message": "Item at index 1 is not a JSON object.",
        })

        docs = json.dumps([{"ok": 1}, "bad"])
        result = await _get_fn(insert_many)("mydb", "users", docs)

        assert "Error" in result
        assert "index 1" in result


class TestCreateCollectionTool:
    async def test_creates_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collection": "products",
        })

        result = await _get_fn(create_collection)("mydb", "products")

        assert "products" in result
        assert "created" in result
        assert "mydb" in result

    async def test_already_exists(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(return_value={
            "status": "error",
            "message": "Collection 'users' already exists in database 'mydb'.",
        })

        result = await _get_fn(create_collection)("mydb", "users")

        assert "Error" in result
        assert "already exists" in result

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_collection

        mock_mongodb_service.create_collection = AsyncMock(
            side_effect=PermissionError("read-only mode")
        )

        result = await _get_fn(create_collection)("mydb", "new_col")

        assert "Error" in result
        assert "read-only" in result


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
        result = await _get_fn(create_index)("mydb", "users", keys)

        assert "name_1_age_-1" in result
        assert "created" in result
        assert "mydb.users" in result

    async def test_invalid_json_keys(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        result = await _get_fn(create_index)("mydb", "users", "not json")

        assert "Error" in result
        assert "valid JSON" in result

    async def test_keys_not_array(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        result = await _get_fn(create_index)("mydb", "users", '{"field": 1}')

        assert "Error" in result
        assert "JSON array" in result

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import create_index

        mock_mongodb_service.create_index = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        keys = json.dumps([["name", 1]])
        result = await _get_fn(create_index)("mydb", "uesrs", keys)

        assert "not found" in result.lower() or "Not found" in result
        assert "users" in result
