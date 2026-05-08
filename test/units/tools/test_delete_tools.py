"""Unit tests for delete tools layer."""
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


# ── delete_one ────────────────────────────────────────────────────────────────


class TestDeleteOneTool:
    async def test_deletes_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        mock_mongodb_service.delete_one = AsyncMock(return_value={
            "status": "ok",
            "deleted_count": 1,
        })

        raw = await _get_fn(delete_one)("mydb", "users", '{"name": "Alice"}')

        assert "Deleted 1" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_deletes_zero_matches(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        mock_mongodb_service.delete_one = AsyncMock(return_value={
            "status": "ok",
            "deleted_count": 0,
        })

        raw = await _get_fn(delete_one)("mydb", "users", '{"name": "Ghost"}')

        assert "Deleted 0" in _unwrap(raw)

    async def test_invalid_json_filter(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        raw = await _get_fn(delete_one)("mydb", "users", "not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        mock_mongodb_service.delete_one = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(delete_one)("mydb", "uesrs", '{}')

        assert "not found" in _unwrap(raw).lower()
        assert "users" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        mock_mongodb_service.delete_one = AsyncMock(return_value={
            "status": "error",
            "message": "filter must be a JSON object.",
        })

        raw = await _get_fn(delete_one)("mydb", "users", '[]')

        assert "Error" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_one

        mock_mongodb_service.delete_one = AsyncMock(
            side_effect=PermissionError("Destructive operations are disabled.")
        )

        raw = await _get_fn(delete_one)("mydb", "users", '{"name": "Alice"}')

        assert "Error" in _unwrap(raw)
        assert "Destructive" in _unwrap(raw)


# ── delete_many ───────────────────────────────────────────────────────────────


class TestDeleteManyTool:
    async def test_deletes_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_many

        mock_mongodb_service.delete_many = AsyncMock(return_value={
            "status": "ok",
            "deleted_count": 7,
        })

        raw = await _get_fn(delete_many)("mydb", "users", '{"active": false}')

        assert "Deleted 7" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_deletes_all_with_empty_filter(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_many

        mock_mongodb_service.delete_many = AsyncMock(return_value={
            "status": "ok",
            "deleted_count": 100,
        })

        raw = await _get_fn(delete_many)("mydb", "users", '{}')

        assert "Deleted 100" in _unwrap(raw)

    async def test_invalid_json_filter(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_many

        raw = await _get_fn(delete_many)("mydb", "users", "{bad}")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_many

        mock_mongodb_service.delete_many = AsyncMock(return_value={
            "status": "not_found",
            "label": "Database",
            "name": "nodb",
            "suggestions": ["mydb"],
        })

        raw = await _get_fn(delete_many)("nodb", "users", '{}')

        assert "not found" in _unwrap(raw).lower()
        assert "mydb" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import delete_many

        mock_mongodb_service.delete_many = AsyncMock(
            side_effect=PermissionError("Destructive operations are disabled.")
        )

        raw = await _get_fn(delete_many)("mydb", "users", '{}')

        assert "Error" in _unwrap(raw)
        assert "Destructive" in _unwrap(raw)


# ── drop_collection ───────────────────────────────────────────────────────────


class TestDropCollectionTool:
    async def test_drops_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_collection

        mock_mongodb_service.drop_collection = AsyncMock(return_value={"status": "ok"})

        raw = await _get_fn(drop_collection)("mydb", "users")

        assert "users" in _unwrap(raw)
        assert "dropped" in _unwrap(raw).lower()
        assert "mydb" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_collection

        mock_mongodb_service.drop_collection = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users", "orders"],
        })

        raw = await _get_fn(drop_collection)("mydb", "uesrs")

        assert "not found" in _unwrap(raw).lower()
        assert "users" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_collection

        mock_mongodb_service.drop_collection = AsyncMock(return_value={
            "status": "error",
            "message": "drop failed",
        })

        raw = await _get_fn(drop_collection)("mydb", "users")

        assert "Error" in _unwrap(raw)
        assert "drop failed" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_collection

        mock_mongodb_service.drop_collection = AsyncMock(
            side_effect=PermissionError("Destructive operations are disabled.")
        )

        raw = await _get_fn(drop_collection)("mydb", "users")

        assert "Error" in _unwrap(raw)
        assert "Destructive" in _unwrap(raw)


# ── drop_database ─────────────────────────────────────────────────────────────


class TestDropDatabaseTool:
    async def test_drops_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_database

        mock_mongodb_service.drop_database = AsyncMock(return_value={"status": "ok"})

        raw = await _get_fn(drop_database)("mydb")

        assert "mydb" in _unwrap(raw)
        assert "dropped" in _unwrap(raw).lower()

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_database

        mock_mongodb_service.drop_database = AsyncMock(return_value={
            "status": "not_found",
            "label": "Database",
            "name": "mydbb",
            "suggestions": ["mydb"],
        })

        raw = await _get_fn(drop_database)("mydbb")

        assert "not found" in _unwrap(raw).lower()
        assert "mydb" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_database

        mock_mongodb_service.drop_database = AsyncMock(return_value={
            "status": "error",
            "message": "insufficient permissions",
        })

        raw = await _get_fn(drop_database)("mydb")

        assert "Error" in _unwrap(raw)
        assert "insufficient permissions" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_database

        mock_mongodb_service.drop_database = AsyncMock(
            side_effect=PermissionError("Destructive operations are disabled.")
        )

        raw = await _get_fn(drop_database)("mydb")

        assert "Error" in _unwrap(raw)
        assert "Destructive" in _unwrap(raw)


# ── drop_index ────────────────────────────────────────────────────────────────


class TestDropIndexTool:
    async def test_drops_and_formats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_index

        mock_mongodb_service.drop_index = AsyncMock(return_value={"status": "ok"})

        raw = await _get_fn(drop_index)("mydb", "users", "name_1")

        assert "name_1" in _unwrap(raw)
        assert "dropped" in _unwrap(raw).lower()
        assert "mydb.users" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_index

        mock_mongodb_service.drop_index = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(drop_index)("mydb", "uesrs", "name_1")

        assert "not found" in _unwrap(raw).lower()
        assert "users" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_index

        mock_mongodb_service.drop_index = AsyncMock(return_value={
            "status": "error",
            "message": "index not found in db",
        })

        raw = await _get_fn(drop_index)("mydb", "users", "bad_index")

        assert "Error" in _unwrap(raw)
        assert "index not found in db" in _unwrap(raw)

    async def test_permission_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import drop_index

        mock_mongodb_service.drop_index = AsyncMock(
            side_effect=PermissionError("Destructive operations are disabled.")
        )

        raw = await _get_fn(drop_index)("mydb", "users", "name_1")

        assert "Error" in _unwrap(raw)
        assert "Destructive" in _unwrap(raw)
