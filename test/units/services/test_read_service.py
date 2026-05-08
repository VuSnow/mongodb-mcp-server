"""Unit tests for ReadService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mongodb_mcp.services.mongodb.read import ReadService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    return ReadService()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.find = AsyncMock(return_value=[
        {"_id": "1", "name": "Alice"},
        {"_id": "2", "name": "Bob"},
    ])
    client.aggregate = AsyncMock(return_value=[
        {"_id": "active", "count": 42},
    ])
    client.count_documents = AsyncMock(return_value=100)
    client.distinct = AsyncMock(return_value=["active", "inactive", "pending"])
    client.list_database_names = AsyncMock(return_value=[
        {"name": "mydb", "size": 1024},
    ])
    client.list_collection_names = AsyncMock(return_value=["users", "orders"])
    return client


@pytest.fixture
def patch_connected(mock_client):
    with patch("mongodb_mcp.services.mongodb.base.connection_manager") as mock_cm:
        from mongodb_mcp.services.connection_manager import ConnectionState
        mock_cm.state = ConnectionState.CONNECTED
        mock_cm.get_client.return_value = mock_client
        yield mock_cm


class TestFind:
    async def test_returns_documents(self, service, mock_client, patch_connected):
        result = await service.find("mydb", "users")

        assert result["status"] == "ok"
        assert len(result["documents"]) == 2
        assert result["count"] == 2
        mock_client.find.assert_awaited_once()

    async def test_with_filter_and_projection(self, service, mock_client, patch_connected):
        mock_client.find.return_value = [{"_id": "1", "name": "Alice"}]

        result = await service.find(
            "mydb", "users",
            filter={"age": {"$gt": 25}},
            projection={"name": 1},
        )

        assert result["status"] == "ok"
        assert result["count"] == 1

    async def test_with_sort(self, service, mock_client, patch_connected):
        result = await service.find("mydb", "users", sort=[["name", 1]])

        assert result["status"] == "ok"
        call_kwargs = mock_client.find.call_args
        assert call_kwargs.kwargs["sort"] == [("name", 1)]

    async def test_invalid_sort_format(self, service, mock_client, patch_connected):
        result = await service.find("mydb", "users", sort=[["name"]])

        assert result["status"] == "error"
        assert "direction" in result["message"].lower() or "field_name" in result["message"]

    async def test_empty_result_resolves(self, service, mock_client, patch_connected):
        mock_client.find.return_value = []
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.find("mydb", "users")

        assert result["status"] == "ok"
        assert result["documents"] == []

    async def test_empty_result_not_found(self, service, mock_client, patch_connected):
        mock_client.find.return_value = []
        mock_client.list_collection_names.return_value = ["orders", "products"]

        result = await service.find("mydb", "uesrs")

        assert result["status"] == "not_found"
        assert "suggestions" in result

    async def test_clamps_limit(self, service, mock_client, patch_connected):
        await service.find("mydb", "users", limit=5000)

        call_kwargs = mock_client.find.call_args
        assert call_kwargs.kwargs["limit"] == 1000

    async def test_validates_empty_database(self, service, patch_connected):
        with pytest.raises(ValueError, match="Database name"):
            await service.find("", "users")

    async def test_exception_resolves(self, service, mock_client, patch_connected):
        mock_client.find.side_effect = Exception("collection not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.find("mydb", "uesrs")

        assert result["status"] == "not_found"


class TestAggregate:
    async def test_returns_results(self, service, mock_client, patch_connected):
        pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
        result = await service.aggregate("mydb", "users", pipeline)

        assert result["status"] == "ok"
        assert result["count"] == 1
        mock_client.aggregate.assert_awaited_once()

    async def test_rejects_empty_pipeline(self, service, patch_connected):
        result = await service.aggregate("mydb", "users", [])

        assert result["status"] == "error"
        assert "non-empty" in result["message"]

    async def test_rejects_non_dict_stage(self, service, patch_connected):
        result = await service.aggregate("mydb", "users", [{"$match": {}}, "bad"])

        assert result["status"] == "error"
        assert "index 1" in result["message"]

    async def test_not_found_on_exception(self, service, mock_client, patch_connected):
        mock_client.aggregate.side_effect = Exception("ns not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.aggregate("mydb", "uesrs", [{"$match": {}}])

        assert result["status"] == "not_found"

    async def test_clamps_limit(self, service, mock_client, patch_connected):
        await service.aggregate("mydb", "users", [{"$match": {}}], limit=50000)

        call_kwargs = mock_client.aggregate.call_args
        assert call_kwargs.kwargs["limit"] == 10000


class TestCountDocuments:
    async def test_returns_count(self, service, mock_client, patch_connected):
        result = await service.count_documents("mydb", "users")

        assert result["status"] == "ok"
        assert result["count"] == 100

    async def test_with_filter(self, service, mock_client, patch_connected):
        mock_client.count_documents.return_value = 42

        result = await service.count_documents("mydb", "users", filter={"active": True})

        assert result["status"] == "ok"
        assert result["count"] == 42

    async def test_not_found_on_exception(self, service, mock_client, patch_connected):
        mock_client.count_documents.side_effect = Exception("ns not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.count_documents("mydb", "uesrs")

        assert result["status"] == "not_found"

    async def test_validates_empty_collection(self, service, patch_connected):
        with pytest.raises(ValueError, match="Collection name"):
            await service.count_documents("mydb", "")


class TestDistinct:
    async def test_returns_values(self, service, mock_client, patch_connected):
        result = await service.distinct("mydb", "users", "status")

        assert result["status"] == "ok"
        assert result["count"] == 3
        assert "active" in result["values"]
        mock_client.distinct.assert_awaited_once()

    async def test_with_filter(self, service, mock_client, patch_connected):
        mock_client.distinct.return_value = ["active"]

        result = await service.distinct("mydb", "users", "status", filter={"age": {"$gt": 25}})

        assert result["status"] == "ok"
        assert result["count"] == 1
        call_kwargs = mock_client.distinct.call_args
        assert call_kwargs.kwargs["filter"] == {"age": {"$gt": 25}}

    async def test_empty_field_rejected(self, service, patch_connected):
        result = await service.distinct("mydb", "users", "")

        assert result["status"] == "error"
        assert "field" in result["message"].lower()

    async def test_not_found_on_exception(self, service, mock_client, patch_connected):
        mock_client.distinct.side_effect = Exception("ns not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.distinct("mydb", "uesrs", "status")

        assert result["status"] == "not_found"

    async def test_validates_empty_database(self, service, patch_connected):
        with pytest.raises(ValueError, match="Database name"):
            await service.distinct("", "users", "status")
