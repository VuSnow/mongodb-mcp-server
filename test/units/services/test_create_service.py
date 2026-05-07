"""Unit tests for CreateService."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from mongodb_mcp.services.mongodb.create import CreateService


pytestmark = pytest.mark.asyncio


@pytest.fixture
def service():
    return CreateService()


@pytest.fixture
def mock_client():
    client = MagicMock()
    client.insert_one = AsyncMock()
    client.insert_many = AsyncMock()
    client.create_collection = AsyncMock()
    client.create_index = AsyncMock()
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
def patch_write_allowed():
    with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
        mock_cfg.read_only = False
        yield mock_cfg


class TestInsertOne:
    async def test_inserts_document(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.insert_one.return_value = MagicMock(inserted_id="abc123")

        result = await service.insert_one("mydb", "users", {"name": "Alice"})

        assert result["status"] == "ok"
        assert result["inserted_id"] == "abc123"
        mock_client.insert_one.assert_awaited_once_with("mydb", "users", {"name": "Alice"})

    async def test_rejects_empty_document(self, service, patch_connected, patch_write_allowed):
        result = await service.insert_one("mydb", "users", {})

        assert result["status"] == "error"
        assert "non-empty" in result["message"]

    async def test_rejects_non_dict_document(self, service, patch_connected, patch_write_allowed):
        result = await service.insert_one("mydb", "users", "not a dict")

        assert result["status"] == "error"

    async def test_blocks_in_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = True
            with pytest.raises(PermissionError):
                await service.insert_one("mydb", "users", {"name": "Alice"})

    async def test_validates_empty_database(self, service, patch_connected, patch_write_allowed):
        with pytest.raises(ValueError, match="Database name"):
            await service.insert_one("", "users", {"name": "Alice"})

    async def test_handles_pymongo_exception(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.insert_one.side_effect = Exception("duplicate key")

        result = await service.insert_one("mydb", "users", {"name": "Alice"})

        assert result["status"] == "error"
        assert "duplicate key" in result["message"]


class TestInsertMany:
    async def test_inserts_multiple(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.insert_many.return_value = MagicMock(inserted_ids=["id1", "id2", "id3"])

        docs = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = await service.insert_many("mydb", "users", docs)

        assert result["status"] == "ok"
        assert result["inserted_count"] == 3
        assert len(result["inserted_ids"]) == 3

    async def test_rejects_empty_list(self, service, patch_connected, patch_write_allowed):
        result = await service.insert_many("mydb", "users", [])

        assert result["status"] == "error"
        assert "non-empty" in result["message"]

    async def test_rejects_non_dict_item(self, service, patch_connected, patch_write_allowed):
        result = await service.insert_many("mydb", "users", [{"ok": 1}, "bad"])

        assert result["status"] == "error"
        assert "index 1" in result["message"]

    async def test_blocks_in_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = True
            with pytest.raises(PermissionError):
                await service.insert_many("mydb", "users", [{"a": 1}])


class TestCreateCollection:
    async def test_creates_collection(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.create_collection("mydb", "products")

        assert result["status"] == "ok"
        assert result["collection"] == "products"
        mock_client.create_collection.assert_awaited_once_with("mydb", "products")

    async def test_rejects_existing_collection(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.create_collection("mydb", "users")

        assert result["status"] == "error"
        assert "already exists" in result["message"]
        mock_client.create_collection.assert_not_awaited()

    async def test_blocks_in_read_only(self, service, patch_connected):
        with patch("mongodb_mcp.services.mongodb.base.configs") as mock_cfg:
            mock_cfg.read_only = True
            with pytest.raises(PermissionError):
                await service.create_collection("mydb", "new_col")


class TestCreateIndex:
    async def test_creates_index(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users"]
        mock_client.create_index.return_value = "name_1"

        result = await service.create_index("mydb", "users", [["name", 1]])

        assert result["status"] == "ok"
        assert result["index_name"] == "name_1"
        mock_client.create_index.assert_awaited_once()

    async def test_creates_unique_index(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users"]
        mock_client.create_index.return_value = "email_1"

        result = await service.create_index("mydb", "users", [["email", 1]], unique=True)

        assert result["status"] == "ok"

    async def test_not_found_collection(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users", "orders"]

        result = await service.create_index("mydb", "uesrs", [["name", 1]])

        assert result["status"] == "not_found"
        assert "suggestions" in result

    async def test_rejects_invalid_keys(self, service, mock_client, patch_connected, patch_write_allowed):
        result = await service.create_index("mydb", "users", "not a list")

        assert result["status"] == "error"
        assert "Keys must be" in result["message"]

    async def test_rejects_bad_key_format(self, service, mock_client, patch_connected, patch_write_allowed):
        mock_client.list_collection_names.return_value = ["users"]

        result = await service.create_index("mydb", "users", [["name"]])

        assert result["status"] == "error"
        assert "direction" in result["message"].lower() or "field_name" in result["message"]
