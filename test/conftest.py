"""Shared fixtures for all tests."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_mongodb_client():
    """Mock MongoDBClient with all methods as AsyncMock."""
    client = MagicMock()
    client.ping = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.list_database_names = AsyncMock(return_value=[
        {"name": "production", "size": 1024000},
        {"name": "staging", "size": 512000},
        {"name": "test", "size": 256000},
    ])
    client.list_collection_names = AsyncMock(return_value=[
        "users", "orders", "products", "user_sessions", "user_logs",
    ])
    client.collection_schema = AsyncMock(return_value=[
        {"_id": "1", "name": "Alice", "age": 30},
        {"_id": "2", "name": "Bob", "age": 25},
    ])
    client.collection_indexes = AsyncMock(return_value=[
        {"v": 2, "key": {"_id": 1}, "name": "_id_"},
        {"v": 2, "key": {"name": 1}, "name": "name_1"},
    ])
    client.db_stats = AsyncMock(return_value={
        "db": "production",
        "collections": 5,
        "objects": 1000,
        "dataSize": 2048000,
    })
    client.explain = AsyncMock(return_value={
        "queryPlanner": {"winningPlan": {"stage": "COLLSCAN"}},
    })
    client.get_logs = AsyncMock(return_value={
        "logs": ["line1", "line2", "line3"],
        "total_lines_written": 100,
    })
    client.find = AsyncMock(return_value=[
        {"_id": "1", "name": "Alice", "age": 30},
        {"_id": "2", "name": "Bob", "age": 25},
    ])
    client.aggregate = AsyncMock(return_value=[
        {"_id": "active", "count": 42},
    ])
    client.count_documents = AsyncMock(return_value=100)
    client.insert_one = AsyncMock()
    client.insert_many = AsyncMock()
    client.create_collection = AsyncMock()
    client.create_index = AsyncMock()
    client.distinct = AsyncMock(return_value=["active", "inactive", "pending"])
    client.collection_stats = AsyncMock(return_value={
        "count": 1000,
        "size": 2048000,
        "avgObjSize": 2048,
        "storageSize": 4096000,
        "totalIndexSize": 512000,
        "nindexes": 3,
    })
    return client


@pytest.fixture
def patch_connection_manager(mock_mongodb_client):
    """Patch ConnectionManager to appear connected with mock client."""
    with patch("mongodb_mcp.services.mongodb.base.connection_manager") as mock_cm:
        mock_cm.state = "connected"
        mock_cm.get_client.return_value = mock_mongodb_client
        mock_cm.connect = AsyncMock()
        yield mock_cm


@pytest.fixture
def patch_configs():
    """Patch configs with default values."""
    with patch("mongodb_mcp.services.mongodb.base.configs") as mock_configs:
        mock_configs.read_only = True
        mock_configs.default_timeout_ms = 30000
        mock_configs.connection_string = "mongodb://localhost:27017"
        mock_configs.write_allowlist = None
        yield mock_configs
