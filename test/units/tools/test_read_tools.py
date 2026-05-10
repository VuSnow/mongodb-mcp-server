"""Unit tests for read tools layer."""
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
    with patch("mongodb_mcp.tools.mongodb.read.mongodb_service") as mock_svc:
        yield mock_svc


class TestFindTool:
    async def test_returns_formatted(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        mock_mongodb_service.find = AsyncMock(return_value={
            "status": "ok",
            "documents": [{"_id": "1", "name": "Alice"}],
            "count": 1,
        })

        raw = await _get_fn(find)("mydb", "users")

        assert "Found 1 documents" in _unwrap(raw)
        assert "Alice" in _unwrap(raw)

    async def test_empty_result(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        mock_mongodb_service.find = AsyncMock(return_value={
            "status": "ok",
            "documents": [],
            "count": 0,
        })

        raw = await _get_fn(find)("mydb", "users")

        assert "0 documents" in _unwrap(raw)

    async def test_invalid_filter_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        raw = await _get_fn(find)("mydb", "users", filter="not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_invalid_projection_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        raw = await _get_fn(find)("mydb", "users", projection="{bad")

        assert "Error" in _unwrap(raw)
        assert "projection" in _unwrap(raw)

    async def test_invalid_sort_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        raw = await _get_fn(find)("mydb", "users", sort="not json")

        assert "Error" in _unwrap(raw)
        assert "sort" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        mock_mongodb_service.find = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(find)("mydb", "uesrs")

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)
        assert "users" in _unwrap(raw)

    async def test_with_all_params(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import find

        mock_mongodb_service.find = AsyncMock(return_value={
            "status": "ok",
            "documents": [{"name": "Alice"}],
            "count": 1,
        })

        raw = await _get_fn(find)(
            "mydb", "users",
            filter='{"age": {"$gt": 25}}',
            projection='{"name": 1}',
            sort='[["name", 1]]',
            skip=5,
            limit=20,
        )

        assert "Found 1 documents" in _unwrap(raw)
        call_kwargs = mock_mongodb_service.find.call_args
        assert call_kwargs.kwargs["filter"] == {"age": {"$gt": 25}}
        assert call_kwargs.kwargs["projection"] == {"name": 1}
        assert call_kwargs.kwargs["sort"] == [["name", 1]]


class TestAggregateTool:
    async def test_returns_formatted(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import aggregate

        mock_mongodb_service.aggregate = AsyncMock(return_value={
            "status": "ok",
            "results": [{"_id": "active", "count": 42}],
            "count": 1,
        })

        pipeline = json.dumps([{"$group": {"_id": "$status", "count": {"$sum": 1}}}])
        raw = await _get_fn(aggregate)("mydb", "users", pipeline)

        assert "1 results" in _unwrap(raw)
        assert "active" in _unwrap(raw)

    async def test_invalid_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import aggregate

        raw = await _get_fn(aggregate)("mydb", "users", "not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_not_array(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import aggregate

        raw = await _get_fn(aggregate)("mydb", "users", '{"$match": {}}')

        assert "Error" in _unwrap(raw)
        assert "JSON array" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import aggregate

        mock_mongodb_service.aggregate = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        pipeline = json.dumps([{"$match": {}}])
        raw = await _get_fn(aggregate)("mydb", "uesrs", pipeline)

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)


class TestCountDocumentsTool:
    async def test_returns_count(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import count_documents

        mock_mongodb_service.count_documents = AsyncMock(return_value={
            "status": "ok",
            "count": 100,
        })

        raw = await _get_fn(count_documents)("mydb", "users")

        assert "100" in _unwrap(raw)
        assert "mydb.users" in _unwrap(raw)

    async def test_invalid_filter(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import count_documents

        raw = await _get_fn(count_documents)("mydb", "users", filter="bad")

        assert "Error" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import count_documents

        mock_mongodb_service.count_documents = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(count_documents)("mydb", "uesrs")

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)


class TestDistinctTool:
    async def test_returns_values(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import distinct

        mock_mongodb_service.distinct = AsyncMock(return_value={
            "status": "ok",
            "field": "status",
            "values": ["active", "inactive", "pending"],
            "count": 3,
        })

        raw = await _get_fn(distinct)("mydb", "users", "status")

        assert "3 distinct values" in _unwrap(raw)
        assert "active" in _unwrap(raw)
        assert "inactive" in _unwrap(raw)

    async def test_invalid_filter_json(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import distinct

        raw = await _get_fn(distinct)("mydb", "users", "status", filter="not json")

        assert "Error" in _unwrap(raw)
        assert "valid JSON" in _unwrap(raw)

    async def test_not_found(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import distinct

        mock_mongodb_service.distinct = AsyncMock(return_value={
            "status": "not_found",
            "label": "Collection",
            "name": "uesrs",
            "suggestions": ["users"],
        })

        raw = await _get_fn(distinct)("mydb", "uesrs", "status")

        assert "not found" in _unwrap(raw).lower() or "Not found" in _unwrap(raw)

    async def test_error_from_service(self, mock_mongodb_service):
        from mongodb_mcp.tools.mongodb import distinct

        mock_mongodb_service.distinct = AsyncMock(return_value={
            "status": "error",
            "message": "field is required and cannot be empty.",
        })

        raw = await _get_fn(distinct)("mydb", "users", "")

        assert "Error" in _unwrap(raw)
        assert "field" in _unwrap(raw).lower()
