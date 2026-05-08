"""Unit tests for DeleteService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mongodb_mcp.services.mongodb.delete import DeleteService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    return DeleteService()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.delete_one = AsyncMock()
    client.delete_many = AsyncMock()
    client.drop_collection = AsyncMock()
    client.drop_database = AsyncMock()
    client.drop_index = AsyncMock()
    client.list_database_names = AsyncMock(return_value=[{"name": "mydb"}, {"name": "otherdb"}])
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
def patch_destructive_allowed():
    with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
        mock_cfg.read_only = False
        mock_cfg.allow_destructive = True
        mock_cfg.write_allowlist = ""
        yield mock_cfg


# ── delete_one ────────────────────────────────────────────────────────────────


class TestDeleteOne:
    async def test_deletes_matching_document(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_one.return_value = MagicMock(deleted_count=1)

        result = await service.delete_one("mydb", "users", {"name": "Alice"})

        assert result["status"] == "ok"
        assert result["deleted_count"] == 1
        mock_client.delete_one.assert_awaited_once_with("mydb", "users", {"name": "Alice"})

    async def test_returns_zero_when_no_match(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_one.return_value = MagicMock(deleted_count=0)

        result = await service.delete_one("mydb", "users", {"name": "Ghost"})

        assert result["status"] == "ok"
        assert result["deleted_count"] == 0

    async def test_rejects_non_dict_filter(self, service, patch_connected, patch_destructive_allowed):
        result = await service.delete_one("mydb", "users", "not a dict")

        assert result["status"] == "error"
        assert "filter" in result["message"]

    async def test_blocks_when_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = True
            mock_cfg.allow_destructive = True
            with pytest.raises(PermissionError):
                await service.delete_one("mydb", "users", {"name": "Alice"})

    async def test_blocks_when_destructive_disabled(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = False
            mock_cfg.allow_destructive = False
            with pytest.raises(PermissionError):
                await service.delete_one("mydb", "users", {"name": "Alice"})

    async def test_validates_empty_database(self, service, patch_connected, patch_destructive_allowed):
        with pytest.raises(ValueError, match="Database name"):
            await service.delete_one("", "users", {"name": "Alice"})

    async def test_validates_empty_collection(self, service, patch_connected, patch_destructive_allowed):
        with pytest.raises(ValueError, match="Collection name"):
            await service.delete_one("mydb", "", {"name": "Alice"})

    async def test_not_found_database(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_database_names.return_value = [{"name": "mydb"}, {"name": "otherdb"}]

        result = await service.delete_one("nonexistent", "users", {"name": "Alice"})

        assert result["status"] == "not_found"
        assert result["label"] == "Database"

    async def test_not_found_collection_with_suggestion(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.delete_one("mydb", "uesrs", {"name": "Alice"})

        assert result["status"] == "not_found"
        assert result["label"] == "Collection"
        assert "users" in result["suggestions"]

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_one.side_effect = Exception("write conflict")

        result = await service.delete_one("mydb", "users", {"name": "Alice"})

        assert result["status"] == "error"
        assert "write conflict" in result["message"]


# ── delete_many ───────────────────────────────────────────────────────────────


class TestDeleteMany:
    async def test_deletes_multiple_documents(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_many.return_value = MagicMock(deleted_count=5)

        result = await service.delete_many("mydb", "users", {"active": False})

        assert result["status"] == "ok"
        assert result["deleted_count"] == 5
        mock_client.delete_many.assert_awaited_once_with("mydb", "users", {"active": False})

    async def test_deletes_all_with_empty_filter(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_many.return_value = MagicMock(deleted_count=42)

        result = await service.delete_many("mydb", "users", {})

        assert result["status"] == "ok"
        assert result["deleted_count"] == 42

    async def test_rejects_non_dict_filter(self, service, patch_connected, patch_destructive_allowed):
        result = await service.delete_many("mydb", "users", ["bad"])

        assert result["status"] == "error"
        assert "filter" in result["message"]

    async def test_blocks_when_destructive_disabled(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = False
            mock_cfg.allow_destructive = False
            with pytest.raises(PermissionError):
                await service.delete_many("mydb", "users", {})

    async def test_not_found_returns_suggestions(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.delete_many("mydb", "orsers", {})

        assert result["status"] == "not_found"
        assert "orders" in result["suggestions"]

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.delete_many.side_effect = Exception("network error")

        result = await service.delete_many("mydb", "users", {})

        assert result["status"] == "error"
        assert "network error" in result["message"]


# ── drop_collection ───────────────────────────────────────────────────────────


class TestDropCollection:
    async def test_drops_collection(self, service, mock_client, patch_connected, patch_destructive_allowed):
        result = await service.drop_collection("mydb", "users")

        assert result["status"] == "ok"
        mock_client.drop_collection.assert_awaited_once_with("mydb", "users")

    async def test_blocks_when_destructive_disabled(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = False
            mock_cfg.allow_destructive = False
            with pytest.raises(PermissionError):
                await service.drop_collection("mydb", "users")

    async def test_validates_empty_names(self, service, patch_connected, patch_destructive_allowed):
        with pytest.raises(ValueError):
            await service.drop_collection("", "users")

    async def test_not_found_collection(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.drop_collection("mydb", "prducts")

        assert result["status"] == "not_found"
        assert result["label"] == "Collection"

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.drop_collection.side_effect = Exception("drop failed")

        result = await service.drop_collection("mydb", "users")

        assert result["status"] == "error"
        assert "drop failed" in result["message"]


# ── drop_database ─────────────────────────────────────────────────────────────


class TestDropDatabase:
    async def test_drops_database(self, service, mock_client, patch_connected, patch_destructive_allowed):
        result = await service.drop_database("mydb")

        assert result["status"] == "ok"
        mock_client.drop_database.assert_awaited_once_with("mydb")

    async def test_blocks_when_destructive_disabled(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = False
            mock_cfg.allow_destructive = False
            with pytest.raises(PermissionError):
                await service.drop_database("mydb")

    async def test_validates_empty_name(self, service, patch_connected, patch_destructive_allowed):
        with pytest.raises(ValueError, match="Database name"):
            await service.drop_database("")

    async def test_not_found_database_with_suggestion(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_database_names.return_value = [{"name": "mydb"}, {"name": "otherdb"}]

        result = await service.drop_database("mydbb")

        assert result["status"] == "not_found"
        assert result["label"] == "Database"
        assert "mydb" in result["suggestions"]

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.drop_database.side_effect = Exception("insufficient permissions")

        result = await service.drop_database("mydb")

        assert result["status"] == "error"
        assert "insufficient permissions" in result["message"]


# ── drop_index ────────────────────────────────────────────────────────────────


class TestDropIndex:
    async def test_drops_index(self, service, mock_client, patch_connected, patch_destructive_allowed):
        result = await service.drop_index("mydb", "users", "name_1")

        assert result["status"] == "ok"
        mock_client.drop_index.assert_awaited_once_with("mydb", "users", "name_1")

    async def test_rejects_empty_index_name(self, service, patch_connected, patch_destructive_allowed):
        result = await service.drop_index("mydb", "users", "")

        assert result["status"] == "error"
        assert "index_name" in result["message"]

    async def test_rejects_whitespace_index_name(self, service, patch_connected, patch_destructive_allowed):
        result = await service.drop_index("mydb", "users", "   ")

        assert result["status"] == "error"
        assert "index_name" in result["message"]

    async def test_blocks_when_destructive_disabled(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = False
            mock_cfg.allow_destructive = False
            with pytest.raises(PermissionError):
                await service.drop_index("mydb", "users", "name_1")

    async def test_not_found_collection(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.drop_index("mydb", "uesrs", "name_1")

        assert result["status"] == "not_found"
        assert result["label"] == "Collection"
        assert "users" in result["suggestions"]

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_destructive_allowed):
        mock_client.drop_index.side_effect = Exception("index not found in db")

        result = await service.drop_index("mydb", "users", "nonexistent_1")

        assert result["status"] == "error"
        assert "index not found in db" in result["message"]
