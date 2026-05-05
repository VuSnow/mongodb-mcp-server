"""Manages MongoDB connection lifecycle and state."""
from __future__ import annotations
from enum import Enum
from mongodb_mcp.clients.mongodb import MongoDBClient
from mongodb_mcp.configs import configs

class ConnectionState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"

class ConnectionManager:
    """Manages MongoDB connection state. Provides client access to tools."""

    def __init__(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        self._client: MongoDBClient | None = None
        self._error: str | None = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def error(self) -> str | None:
        return self._error

    async def connect(self, connection_string: str | None = None) -> None:
        """Connect to MongoDB. Uses config connection_string if not provided."""
        uri = connection_string or configs.connection_string
        self._state = ConnectionState.CONNECTING
        self._error = None

        try:
            self._client = MongoDBClient(
                uri, timeout_ms=configs.default_timeout_ms)
            await self._client.ping()
            self._state = ConnectionState.CONNECTED
        except Exception as e:
            self._state = ConnectionState.ERROR
            self._error = str(e)
            self._client = None
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self._client:
            await self._client.close()
        self._client = None
        self._state = ConnectionState.DISCONNECTED
        self._error = None

    def get_client(self) -> MongoDBClient:
        """Get the active MongoDB client. Raises if not connected."""
        if self._state != ConnectionState.CONNECTED or not self._client:
            raise ConnectionError(
                f"MongoDB is not connected (state: {self._state.value}). "
                "Use the connect tool first."
            )
        return self._client


# Singleton — shared across all tools
connection_manager = ConnectionManager()