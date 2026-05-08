"""Unit tests for MetadataService."""
import pytest
from unittest.mock import AsyncMock, patch

from mongodb_mcp.services.mongodb.metadata import MetadataService


pytestmark = pytest.mark.asyncio


class TestListDatabases:
    """Tests for list_databases — no resolve."""

    async def test_returns_databases(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.list_databases()

        assert result["status"] == "ok"
        assert len(result["databases"]) == 3
        mock_mongodb_client.list_database_names.assert_awaited_once()


class TestListCollections:
    """Tests for list_collections — no resolve."""

    async def test_returns_collections(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.list_collections("production")

        assert result["status"] == "ok"
        assert result["database"] == "production"
        assert "users" in result["collections"]

    async def test_empty_database_name_raises(self, patch_connection_manager):
        service = MetadataService()
        with pytest.raises(ValueError, match="Database name"):
            await service.list_collections("")


class TestCollectionSchema:
    """Tests for collection_schema — lazy resolve on empty."""

    async def test_returns_documents_on_success(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.collection_schema("production", "users")

        assert result["status"] == "ok"
        assert len(result["documents"]) == 2
        mock_mongodb_client.collection_schema.assert_awaited_once_with(
            database="production", collection="users", sample_size=20
        )

    async def test_triggers_resolve_on_empty_result(self, patch_connection_manager, mock_mongodb_client):
        """When schema returns empty and collection doesn't exist, should return not_found."""
        mock_mongodb_client.collection_schema = AsyncMock(return_value=[])
        # Collection "uesrs" doesn't exist — resolve will check list
        mock_mongodb_client.list_collection_names = AsyncMock(
            return_value=["users", "orders", "products"]
        )

        service = MetadataService()
        result = await service.collection_schema("production", "uesrs")

        assert result["status"] == "not_found"
        assert result["label"] == "Collection"
        assert "users" in result["suggestions"]

    async def test_returns_empty_when_collection_genuinely_empty(self, patch_connection_manager, mock_mongodb_client):
        """When collection exists but is empty, returns ok with empty documents."""
        mock_mongodb_client.collection_schema = AsyncMock(return_value=[])
        # "users" does exist in the list
        mock_mongodb_client.list_collection_names = AsyncMock(
            return_value=["users", "orders"]
        )

        service = MetadataService()
        result = await service.collection_schema("production", "users")

        assert result["status"] == "ok"
        assert result["documents"] == []

    async def test_db_not_found_triggers_resolve(self, patch_connection_manager, mock_mongodb_client):
        """When database doesn't exist, should return not_found for database."""
        mock_mongodb_client.collection_schema = AsyncMock(return_value=[])
        mock_mongodb_client.list_database_names = AsyncMock(return_value=[
            {"name": "production", "size": 1024},
            {"name": "staging", "size": 512},
        ])

        service = MetadataService()
        result = await service.collection_schema("prodution", "users")  # typo

        assert result["status"] == "not_found"
        assert result["label"] == "Database"
        assert "production" in result["suggestions"]

    async def test_sample_size_clamped(self, patch_connection_manager, mock_mongodb_client):
        """sample_size should be clamped between 1 and 100."""
        service = MetadataService()
        await service.collection_schema("production", "users", sample_size=999)

        mock_mongodb_client.collection_schema.assert_awaited_once_with(
            database="production", collection="users", sample_size=100
        )

    async def test_validates_empty_names(self, patch_connection_manager):
        service = MetadataService()
        with pytest.raises(ValueError):
            await service.collection_schema("", "users")
        with pytest.raises(ValueError):
            await service.collection_schema("production", "")


class TestCollectionIndexes:
    """Tests for collection_indexes — lazy resolve on empty."""

    async def test_returns_indexes(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.collection_indexes("production", "users")

        assert result["status"] == "ok"
        assert len(result["indexes"]) == 2

    async def test_triggers_resolve_on_empty(self, patch_connection_manager, mock_mongodb_client):
        mock_mongodb_client.collection_indexes = AsyncMock(return_value=[])
        mock_mongodb_client.list_collection_names = AsyncMock(
            return_value=["users", "orders"]
        )

        service = MetadataService()
        result = await service.collection_indexes("production", "uesrs")

        assert result["status"] == "not_found"
        assert "users" in result["suggestions"]

    async def test_empty_indexes_when_collection_exists(self, patch_connection_manager, mock_mongodb_client):
        mock_mongodb_client.collection_indexes = AsyncMock(return_value=[])
        mock_mongodb_client.list_collection_names = AsyncMock(
            return_value=["users", "orders"]
        )

        service = MetadataService()
        result = await service.collection_indexes("production", "users")

        assert result["status"] == "ok"
        assert result["indexes"] == []


class TestDbStats:
    """Tests for db_stats — resolve on exception."""

    async def test_returns_stats(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.db_stats("production")

        assert result["status"] == "ok"
        assert result["stats"]["db"] == "production"

    async def test_resolve_on_exception_db_not_found(self, patch_connection_manager, mock_mongodb_client):
        mock_mongodb_client.db_stats = AsyncMock(side_effect=Exception("ns not found"))
        mock_mongodb_client.list_database_names = AsyncMock(return_value=[
            {"name": "production", "size": 1024},
            {"name": "staging", "size": 512},
        ])

        service = MetadataService()
        result = await service.db_stats("prodution")  # typo

        assert result["status"] == "not_found"
        assert result["label"] == "Database"
        assert "production" in result["suggestions"]

    async def test_reraise_when_db_exists(self, patch_connection_manager, mock_mongodb_client):
        """If DB exists but error is unrelated, should re-raise."""
        mock_mongodb_client.db_stats = AsyncMock(side_effect=Exception("unknown error"))
        mock_mongodb_client.list_database_names = AsyncMock(return_value=[
            {"name": "production", "size": 1024},
        ])

        service = MetadataService()
        with pytest.raises(Exception, match="unknown error"):
            await service.db_stats("production")


class TestExplain:
    """Tests for explain — resolve on exception."""

    async def test_returns_plan(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.explain("production", "users", "find", {"filter": {}})

        assert result["status"] == "ok"
        assert "queryPlanner" in result["plan"]

    async def test_invalid_method(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.explain("production", "users", "invalid", {})

        assert result["status"] == "error"
        assert "Unsupported method" in result["message"]

    async def test_invalid_verbosity(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.explain("production", "users", "find", {}, verbosity="bad")

        assert result["status"] == "error"
        assert "Unsupported verbosity" in result["message"]

    async def test_resolve_on_exception(self, patch_connection_manager, mock_mongodb_client):
        mock_mongodb_client.explain = AsyncMock(side_effect=Exception("ns not found"))
        mock_mongodb_client.list_collection_names = AsyncMock(
            return_value=["users", "orders"]
        )

        service = MetadataService()
        result = await service.explain("production", "uesrs", "find", {"filter": {}})

        assert result["status"] == "not_found"
        assert "users" in result["suggestions"]


class TestGetLogs:
    """Tests for get_logs — no resolve."""

    async def test_returns_logs(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.get_logs("global", 50)

        assert result["status"] == "ok"
        assert "logs" in result
        assert result["total_lines_written"] == 100

    async def test_invalid_log_type(self, patch_connection_manager):
        service = MetadataService()
        result = await service.get_logs("invalid_type")

        assert result["status"] == "error"
        assert "Invalid log_type" in result["message"]

    async def test_limit_clamped(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        await service.get_logs("global", 9999)

        mock_mongodb_client.get_logs.assert_awaited_once_with("global", 1000)


class TestCollectionStats:
    """Tests for collection_stats — lazy resolve on empty/error."""

    async def test_returns_stats(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        result = await service.collection_stats("production", "users")

        assert result["status"] == "ok"
        assert result["stats"]["count"] == 1000
        assert result["stats"]["storageSize"] == 4096000
        mock_mongodb_client.collection_stats.assert_awaited_once()

    async def test_not_found_on_exception(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        mock_mongodb_client.collection_stats.side_effect = Exception("ns not found")

        result = await service.collection_stats("production", "uesrs")

        assert result["status"] == "not_found"
        assert "suggestions" in result

    async def test_empty_stats_resolves(self, patch_connection_manager, mock_mongodb_client):
        service = MetadataService()
        mock_mongodb_client.collection_stats.return_value = {}

        result = await service.collection_stats("production", "users")

        # "users" exists in mock list_collection_names, so it resolves as empty
        assert result["status"] == "ok"
        assert result["stats"] == {}

    async def test_validates_empty_database(self, patch_connection_manager):
        service = MetadataService()
        with pytest.raises(ValueError, match="Database name"):
            await service.collection_stats("", "users")
