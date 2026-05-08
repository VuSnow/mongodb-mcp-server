"""Unit tests for UpdateService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mongodb_mcp.services.mongodb.update import UpdateService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    return UpdateService()


@pytest.fixture
def mock_client():
    client = MagicMock()
    update_result = MagicMock()
    update_result.matched_count = 1
    update_result.modified_count = 1
    update_result.upserted_id = None
    client.update_one = AsyncMock(return_value=update_result)
    client.update_many = AsyncMock(return_value=update_result)
    client.rename_collection = AsyncMock()
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


@pytest.fixture
def patch_writable():
    with patch("mongodb_mcp.services.mongodb.base.configs") as mock_configs:
        mock_configs.read_only = False
        mock_configs.write_allowlist = None
        yield mock_configs


class TestUpdateOne:
    async def test_updates_document(self, service, mock_client, patch_connected, patch_writable):
        result = await service.update_one("mydb", "users", {"name": "Alice"}, {"$set": {"age": 31}})

        assert result["status"] == "ok"
        assert result["matched_count"] == 1
        assert result["modified_count"] == 1
        mock_client.update_one.assert_awaited_once()

    async def test_with_upsert(self, service, mock_client, patch_connected, patch_writable):
        upsert_result = MagicMock()
        upsert_result.matched_count = 0
        upsert_result.modified_count = 0
        upsert_result.upserted_id = "abc123"
        mock_client.update_one.return_value = upsert_result

        result = await service.update_one("mydb", "users", {"name": "New"}, {"$set": {"age": 25}}, upsert=True)

        assert result["status"] == "ok"
        assert result["upserted_id"] == "abc123"

    async def test_rejects_empty_filter(self, service, patch_connected, patch_writable):
        result = await service.update_one("mydb", "users", {}, {"$set": {"age": 31}})

        assert result["status"] == "error"
        assert "filter" in result["message"]

    async def test_rejects_empty_update(self, service, patch_connected, patch_writable):
        result = await service.update_one("mydb", "users", {"name": "Alice"}, {})

        assert result["status"] == "error"
        assert "update" in result["message"]

    async def test_rejects_non_operator_update(self, service, patch_connected, patch_writable):
        result = await service.update_one("mydb", "users", {"name": "Alice"}, {"name": "Bob"})

        assert result["status"] == "error"
        assert "$set" in result["message"]

    async def test_rejects_unknown_operator(self, service, patch_connected, patch_writable):
        result = await service.update_one("mydb", "users", {"name": "Alice"}, {"$badOp": {"x": 1}})

        assert result["status"] == "error"
        assert "Unknown" in result["message"]

    async def test_blocked_in_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_configs:
            mock_configs.read_only = True
            with pytest.raises(PermissionError, match="read-only"):
                await service.update_one("mydb", "users", {"name": "Alice"}, {"$set": {"age": 31}})

    async def test_not_found_on_exception(self, service, mock_client, patch_connected, patch_writable):
        mock_client.update_one.side_effect = Exception("ns not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.update_one("mydb", "uesrs", {"name": "Alice"}, {"$set": {"age": 31}})

        assert result["status"] == "not_found"

    async def test_validates_empty_database(self, service, patch_connected, patch_writable):
        with pytest.raises(ValueError, match="Database name"):
            await service.update_one("", "users", {"name": "Alice"}, {"$set": {"age": 31}})


class TestUpdateMany:
    async def test_updates_documents(self, service, mock_client, patch_connected, patch_writable):
        many_result = MagicMock()
        many_result.matched_count = 5
        many_result.modified_count = 5
        many_result.upserted_id = None
        mock_client.update_many.return_value = many_result

        result = await service.update_many("mydb", "users", {"active": True}, {"$set": {"verified": True}})

        assert result["status"] == "ok"
        assert result["matched_count"] == 5
        assert result["modified_count"] == 5

    async def test_rejects_non_operator(self, service, patch_connected, patch_writable):
        result = await service.update_many("mydb", "users", {"active": True}, {"status": "inactive"})

        assert result["status"] == "error"
        assert "$set" in result["message"]

    async def test_not_found_on_exception(self, service, mock_client, patch_connected, patch_writable):
        mock_client.update_many.side_effect = Exception("ns not found")
        mock_client.list_collection_names.return_value = ["orders"]

        result = await service.update_many("mydb", "uesrs", {"active": True}, {"$set": {"x": 1}})

        assert result["status"] == "not_found"


class TestRenameCollection:
    async def test_renames_collection(self, service, mock_client, patch_connected, patch_writable):
        result = await service.rename_collection("mydb", "users", "customers")

        assert result["status"] == "ok"
        assert result["old_name"] == "users"
        assert result["new_name"] == "customers"
        mock_client.rename_collection.assert_awaited_once()

    async def test_rejects_same_name(self, service, patch_connected, patch_writable):
        result = await service.rename_collection("mydb", "users", "users")

        assert result["status"] == "error"
        assert "different" in result["message"]

    async def test_rejects_existing_target(self, service, mock_client, patch_connected, patch_writable):
        result = await service.rename_collection("mydb", "users", "orders")

        assert result["status"] == "error"
        assert "already exists" in result["message"]

    async def test_allows_drop_target(self, service, mock_client, patch_connected, patch_writable):
        result = await service.rename_collection("mydb", "users", "orders", drop_target=True)

        assert result["status"] == "ok"
        mock_client.rename_collection.assert_awaited_once()

    async def test_not_found_source(self, service, mock_client, patch_connected, patch_writable):
        mock_client.list_collection_names.return_value = ["orders", "products"]

        result = await service.rename_collection("mydb", "uesrs", "customers")

        assert result["status"] == "not_found"
        assert "suggestions" in result

    async def test_blocked_in_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_configs:
            mock_configs.read_only = True
            with pytest.raises(PermissionError, match="read-only"):
                await service.rename_collection("mydb", "users", "customers")

    async def test_validates_empty_new_name(self, service, patch_connected, patch_writable):
        with pytest.raises(ValueError, match="New collection name"):
            await service.rename_collection("mydb", "users", "")
