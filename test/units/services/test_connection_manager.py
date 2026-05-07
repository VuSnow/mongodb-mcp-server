"""Unit tests for ConnectionManager."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from mongodb_mcp.services.connection_manager import ConnectionManager, ConnectionState


pytestmark = pytest.mark.asyncio


class TestConnectionState:
    """Tests for connection state transitions."""

    def test_initial_state_is_disconnected(self):
        cm = ConnectionManager()
        assert cm.state == ConnectionState.DISCONNECTED
        assert cm.error is None

    async def test_connect_transitions_to_connected(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            MockClient.return_value = mock_instance

            await cm.connect("mongodb://localhost:27017")

            assert cm.state == ConnectionState.CONNECTED
            assert cm.error is None

    async def test_connect_transitions_to_error_on_failure(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(side_effect=Exception("connection refused"))
            MockClient.return_value = mock_instance

            with pytest.raises(ConnectionError, match="Failed to connect"):
                await cm.connect("mongodb://localhost:27017")

            assert cm.state == ConnectionState.ERROR
            assert "connection refused" in cm.error

    async def test_disconnect_transitions_to_disconnected(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            await cm.connect("mongodb://localhost:27017")
            await cm.disconnect()

            assert cm.state == ConnectionState.DISCONNECTED
            assert cm.error is None
            mock_instance.close.assert_awaited_once()


class TestGetClient:
    """Tests for get_client."""

    def test_raises_when_not_connected(self):
        cm = ConnectionManager()
        with pytest.raises(ConnectionError, match="not connected"):
            cm.get_client()

    async def test_returns_client_when_connected(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            MockClient.return_value = mock_instance

            await cm.connect("mongodb://localhost:27017")
            client = cm.get_client()

            assert client == mock_instance

    async def test_raises_after_disconnect(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            mock_instance = MagicMock()
            mock_instance.ping = AsyncMock(return_value=True)
            mock_instance.close = AsyncMock()
            MockClient.return_value = mock_instance

            await cm.connect("mongodb://localhost:27017")
            await cm.disconnect()

            with pytest.raises(ConnectionError):
                cm.get_client()


class TestConnectWithConfig:
    """Tests for connect using config fallback."""

    async def test_uses_config_connection_string_when_none_provided(self):
        cm = ConnectionManager()
        with patch("mongodb_mcp.services.connection_manager.MongoDBClient") as MockClient:
            with patch("mongodb_mcp.services.connection_manager.configs") as mock_configs:
                mock_configs.connection_string = "mongodb://config-host:27017"
                mock_configs.default_timeout_ms = 5000

                mock_instance = MagicMock()
                mock_instance.ping = AsyncMock(return_value=True)
                MockClient.return_value = mock_instance

                await cm.connect(None)

                MockClient.assert_called_once_with(
                    "mongodb://config-host:27017", timeout_ms=5000
                )
