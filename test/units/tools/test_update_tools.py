"""Unit tests for update tools layer."""
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


class TestUpdateOneTool:
    async def test_updates_document(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        mock_mongodb_service.update_one = AsyncMock(return_value={
            "status": "ok",
            "matched_count": 1,
            "modified_count": 1,
            "upserted_id": None,
        })

        raw = await _get_fn(update_one)("mydb", "users", '{"name": "Alice"}', '{"$set": {"age": 31}}')

        assert "Matched 1" in _unwrap(raw)
        assert "modified 1" in _unwrap(raw)

    async def test_with_upsert(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        mock_mongodb_service.update_one = AsyncMock(return_value={
            "status": "ok",
            "matched_count": 0,
            "modified_count": 0,
            "upserted_id": "abc123",
        })

        raw = await _get_fn(update_one)("mydb", "users", '{"name": "New"}', '{"$set": {"age": 25}}', upsert=True)

        assert "abc123" in _unwrap(raw)

    async def test_invalid_filter_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        raw = await _get_fn(update_one)("mydb", "users", "not json", '{"$set": {"x": 1}}')

        assert "Error" in _unwrap(raw)
        assert "filter" in _unwrap(raw)

    async def test_invalid_update_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        raw = await _get_fn(update_one)("mydb", "users", '{"name": "Alice"}', "not json")

        assert "Error" in _unwrap(raw)
        assert "update" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        mock_mongodb_service.update_one = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(update_one)("mydb", "uesrs", '{"name": "Alice"}', '{"$set": {"age": 31}}')

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        mock_mongodb_service.update_one = AsyncMock(return_value={
            "status": "error",
            "message": "update must use operators",
        })

        raw = await _get_fn(update_one)("mydb", "users", '{"name": "Alice"}', '{"$set": {"age": 31}}')

        assert "Error" in _unwrap(raw)
        assert "operators" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_one

        mock_mongodb_service.update_one = AsyncMock(side_effect=PermissionError("read-only"))

        raw = await _get_fn(update_one)("mydb", "users", '{"name": "Alice"}', '{"$set": {"age": 31}}')

        assert "Error" in _unwrap(raw)
        assert "read-only" in _unwrap(raw)


class TestUpdateManyTool:
    async def test_updates_documents(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_many

        mock_mongodb_service.update_many = AsyncMock(return_value={
            "status": "ok",
            "matched_count": 5,
            "modified_count": 5,
            "upserted_id": None,
        })

        raw = await _get_fn(update_many)("mydb", "users", '{"active": true}', '{"$set": {"verified": true}}')

        assert "Matched 5" in _unwrap(raw)
        assert "modified 5" in _unwrap(raw)

    async def test_invalid_filter_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_many

        raw = await _get_fn(update_many)("mydb", "users", "bad", '{"$set": {"x": 1}}')

        assert "Error" in _unwrap(raw)
        assert "filter" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import update_many

        mock_mongodb_service.update_many = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(update_many)("mydb", "uesrs", '{"active": true}', '{"$set": {"x": 1}}')

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)


class TestRenameCollectionTool:
    async def test_renames_collection(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import rename_collection

        mock_mongodb_service.rename_collection = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "old_name": "users",
            "new_name": "customers",
        })

        raw = await _get_fn(rename_collection)("mydb", "users", "customers")

        assert "renamed" in _unwrap(raw).lower()
        assert "customers" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import rename_collection

        mock_mongodb_service.rename_collection = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(rename_collection)("mydb", "uesrs", "customers")

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)

    async def test_error_same_name(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import rename_collection

        mock_mongodb_service.rename_collection = AsyncMock(return_value={
            "status": "error",
            "message": "New name must be different from the current name.",
        })

        raw = await _get_fn(rename_collection)("mydb", "users", "users")

        assert "Error" in _unwrap(raw)
        assert "different" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import rename_collection

        mock_mongodb_service.rename_collection = AsyncMock(side_effect=PermissionError("read-only"))

        raw = await _get_fn(rename_collection)("mydb", "users", "customers")

        assert "Error" in _unwrap(raw)
        assert "read-only" in _unwrap(raw)
