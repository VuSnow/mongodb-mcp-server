"""Unit tests for metadata tools layer."""
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
    with patch("mongodb_mcp.tools.mongodb.metadata.mongodb_service") as mock_svc:
        yield mock_svc


class TestListDatabasesTool:
    async def test_formats_databases(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_databases

        mock_mongodb_service.list_databases = AsyncMock(return_value={
            "status": "ok",
            "databases": [
                {"name": "production", "size": 1024},
                {"name": "test", "size": 512},
            ],
        })

        raw = await _get_fn(list_databases)()

        assert "Found 2 databases" in _unwrap(raw)
        assert "production" in _unwrap(raw)
        assert "test" in _unwrap(raw)

    async def test_handles_connection_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_databases

        mock_mongodb_service.list_databases = AsyncMock(
            side_effect=ConnectionError("not connected")
        )

        raw = await _get_fn(list_databases)()

        assert "Error:" in _unwrap(raw)
        assert "not connected" in _unwrap(raw)


class TestListCollectionsTool:
    async def test_formats_collections(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_collections

        mock_mongodb_service.list_collections = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collections": ["users", "orders"],
        })

        raw = await _get_fn(list_collections)("mydb")

        assert "Found 2 collections" in _unwrap(raw)
        assert "users" in _unwrap(raw)

    async def test_empty_collections(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_collections

        mock_mongodb_service.list_collections = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collections": [],
        })

        raw = await _get_fn(list_collections)("mydb")

        assert "Found 0 collections" in _unwrap(raw)


class TestCollectionSchemaTool:
    async def test_formats_schema(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "ok",
            "documents": [{"_id": "1", "name": "Alice"}],
        })

        raw = await _get_fn(collection_schema)("mydb", "users")

        assert "Sampled 1 documents" in _unwrap(raw)
        assert "Alice" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users", "user_logs"],
        })

        raw = await _get_fn(collection_schema)("mydb", "uesrs")

        assert "not found" in _unwrap(raw)
        assert "Did you mean" in _unwrap(raw)
        assert "users" in _unwrap(raw)
        assert "user_logs" in _unwrap(raw)
        assert "Please confirm" in _unwrap(raw)

    async def test_empty_collection(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "ok",
            "documents": [],
        })

        raw = await _get_fn(collection_schema)("mydb", "users")

        assert "empty" in _unwrap(raw)


class TestCollectionIndexesTool:
    async def test_formats_indexes(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_indexes

        mock_mongodb_service.collection_indexes = AsyncMock(return_value={
            "status": "ok",
            "indexes": [{"name": "_id_", "key": {"_id": 1}}],
        })

        raw = await _get_fn(collection_indexes)("mydb", "users")

        assert "Found 1 indexes" in _unwrap(raw)
        assert "_id_" in _unwrap(raw)

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_indexes

        mock_mongodb_service.collection_indexes = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(collection_indexes)("mydb", "uesrs")

        assert "not found" in _unwrap(raw)
        assert "users" in _unwrap(raw)


class TestDbStatsTool:
    async def test_formats_stats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import db_stats

        mock_mongodb_service.db_stats = AsyncMock(return_value={
            "status": "ok",
            "stats": {"db": "mydb", "collections": 5},
        })

        raw = await _get_fn(db_stats)("mydb")

        assert "Stats for mydb" in _unwrap(raw)
        assert "collections" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import db_stats

        mock_mongodb_service.db_stats = AsyncMock(return_value={
            "status": "not_found",
            "label": "Database",
            "name": "prodution",
            "suggestions": ["production"],
        })

        raw = await _get_fn(db_stats)("prodution")

        assert "not found" in _unwrap(raw)
        assert "production" in _unwrap(raw)


class TestExplainQueryTool:
    async def test_formats_plan(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        mock_mongodb_service.explain = AsyncMock(return_value={
            "status": "ok",
            "plan": {"queryPlanner": {"winningPlan": "IXSCAN"}},
        })

        raw = await _get_fn(explain_query)("mydb", "users", "find", '{"filter": {}}')

        assert "Explain (find, queryPlanner)" in _unwrap(raw)
        assert "IXSCAN" in _unwrap(raw)

    async def test_invalid_json_args(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        raw = await _get_fn(explain_query)("mydb", "users", "find", "not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        mock_mongodb_service.explain = AsyncMock(return_value={
            "status": "error",
            "message": "Unsupported method: bad",
        })

        raw = await _get_fn(explain_query)("mydb", "users", "bad", '{}')

        assert "Error" in _unwrap(raw)
        assert "Unsupported method" in _unwrap(raw)


class TestGetLogsTool:
    async def test_formats_logs(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import get_logs

        mock_mongodb_service.get_logs = AsyncMock(return_value={
            "status": "ok",
            "logs": ["log line 1", "log line 2"],
            "total_lines_written": 500,
        })

        raw = await _get_fn(get_logs)("global", 50)

        assert "Showing 2 of 500" in _unwrap(raw)
        assert "log line 1" in _unwrap(raw)

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import get_logs

        mock_mongodb_service.get_logs = AsyncMock(return_value={
            "status": "error",
            "message": "Invalid log_type: bad",
        })

        raw = await _get_fn(get_logs)("bad")

        assert "Error" in _unwrap(raw)
        assert "Invalid log_type" in _unwrap(raw)


class TestCollectionStatsTool:
    async def test_formats_stats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_stats

        mock_mongodb_service.collection_stats = AsyncMock(return_value={
            "status": "ok",
            "stats": {
                "count": 1000,
                "size": 2048000,
                "avgObjSize": 2048,
                "storageSize": 4096000,
                "totalIndexSize": 512000,
                "nindexes": 3,
            },
        })

        raw = await _get_fn(collection_stats)("mydb", "users")

        assert "Storage stats" in _unwrap(raw)
        assert "1000" in _unwrap(raw)
        assert "4096000" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_stats

        mock_mongodb_service.collection_stats = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(collection_stats)("mydb", "uesrs")

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)
        assert "users" in _unwrap(raw)

    async def test_empty_stats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_stats

        mock_mongodb_service.collection_stats = AsyncMock(return_value={
            "status": "ok",
            "stats": {},
        })

        raw = await _get_fn(collection_stats)("mydb", "users")

        assert "No storage stats" in _unwrap(raw)
