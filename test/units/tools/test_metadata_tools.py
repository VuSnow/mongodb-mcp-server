"""Unit tests for metadata tools layer."""
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

        result = await _get_fn(list_databases)()

        assert "Found 2 databases" in result
        assert "production" in result
        assert "test" in result

    async def test_handles_connection_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_databases

        mock_mongodb_service.list_databases = AsyncMock(
            side_effect=ConnectionError("not connected")
        )

        result = await _get_fn(list_databases)()

        assert "Error:" in result
        assert "not connected" in result


class TestListCollectionsTool:
    async def test_formats_collections(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_collections

        mock_mongodb_service.list_collections = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collections": ["users", "orders"],
        })

        result = await _get_fn(list_collections)("mydb")

        assert "Found 2 collections" in result
        assert "users" in result

    async def test_empty_collections(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import list_collections

        mock_mongodb_service.list_collections = AsyncMock(return_value={
            "status": "ok",
            "database": "mydb",
            "collections": [],
        })

        result = await _get_fn(list_collections)("mydb")

        assert "Found 0 collections" in result


class TestCollectionSchemaTool:
    async def test_formats_schema(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "ok",
            "documents": [{"_id": "1", "name": "Alice"}],
        })

        result = await _get_fn(collection_schema)("mydb", "users")

        assert "Sampled 1 documents" in result
        assert "Alice" in result

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users", "user_logs"],
        })

        result = await _get_fn(collection_schema)("mydb", "uesrs")

        assert "not found" in result
        assert "Did you mean" in result
        assert "users" in result
        assert "user_logs" in result
        assert "Please confirm" in result

    async def test_empty_collection(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_schema

        mock_mongodb_service.collection_schema = AsyncMock(return_value={
            "status": "ok",
            "documents": [],
        })

        result = await _get_fn(collection_schema)("mydb", "users")

        assert "empty" in result


class TestCollectionIndexesTool:
    async def test_formats_indexes(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_indexes

        mock_mongodb_service.collection_indexes = AsyncMock(return_value={
            "status": "ok",
            "indexes": [{"name": "_id_", "key": {"_id": 1}}],
        })

        result = await _get_fn(collection_indexes)("mydb", "users")

        assert "Found 1 indexes" in result
        assert "_id_" in result

    async def test_not_found_shows_suggestions(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import collection_indexes

        mock_mongodb_service.collection_indexes = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        result = await _get_fn(collection_indexes)("mydb", "uesrs")

        assert "not found" in result
        assert "users" in result


class TestDbStatsTool:
    async def test_formats_stats(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import db_stats

        mock_mongodb_service.db_stats = AsyncMock(return_value={
            "status": "ok",
            "stats": {"db": "mydb", "collections": 5},
        })

        result = await _get_fn(db_stats)("mydb")

        assert "Stats for mydb" in result
        assert "collections" in result

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import db_stats

        mock_mongodb_service.db_stats = AsyncMock(return_value={
            "status": "not_found",
            "label": "Database",
            "name": "prodution",
            "suggestions": ["production"],
        })

        result = await _get_fn(db_stats)("prodution")

        assert "not found" in result
        assert "production" in result


class TestExplainQueryTool:
    async def test_formats_plan(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        mock_mongodb_service.explain = AsyncMock(return_value={
            "status": "ok",
            "plan": {"queryPlanner": {"winningPlan": "IXSCAN"}},
        })

        result = await _get_fn(explain_query)("mydb", "users", "find", '{"filter": {}}')

        assert "Explain (find, queryPlanner)" in result
        assert "IXSCAN" in result

    async def test_invalid_json_args(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        result = await _get_fn(explain_query)("mydb", "users", "find", "not json")

        assert "Error" in result
        assert "valid JSON" in result

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import explain_query

        mock_mongodb_service.explain = AsyncMock(return_value={
            "status": "error",
            "message": "Unsupported method: bad",
        })

        result = await _get_fn(explain_query)("mydb", "users", "bad", '{}')

        assert "Error" in result
        assert "Unsupported method" in result


class TestGetLogsTool:
    async def test_formats_logs(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import get_logs

        mock_mongodb_service.get_logs = AsyncMock(return_value={
            "status": "ok",
            "logs": ["log line 1", "log line 2"],
            "total_lines_written": 500,
        })

        result = await _get_fn(get_logs)("global", 50)

        assert "Showing 2 of 500" in result
        assert "log line 1" in result

    async def test_service_error(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import get_logs

        mock_mongodb_service.get_logs = AsyncMock(return_value={
            "status": "error",
            "message": "Invalid log_type: bad",
        })

        result = await _get_fn(get_logs)("bad")

        assert "Error" in result
        assert "Invalid log_type" in result
