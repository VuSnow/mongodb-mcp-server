"""Manages MongoDB connection lifecycle and state."""
from __future__ import annotations

import logging
from enum import Enum

from mongodb_mcp.clients.mongodb import MongoDBClient
from mongodb_mcp.configs import configs

logger = logging.getLogger(__name__)


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
        # Mask URI for logging (show host only, hide credentials)
        masked_uri = uri.split("@")[-1] if "@" in uri else uri
        logger.info(f"[connection] Connecting to {masked_uri} (timeout={configs.default_timeout_ms}ms)")
        self._state = ConnectionState.CONNECTING
        self._error = None

        try:
            self._client = MongoDBClient(uri, timeout_ms=configs.default_timeout_ms)
            await self._client.ping()
            self._state = ConnectionState.CONNECTED
            logger.info(f"[connection] Connected successfully to {masked_uri}")
        except Exception as e:
            self._state = ConnectionState.ERROR
            self._error = str(e)
            self._client = None
            logger.error(f"[connection] Failed to connect to {masked_uri}: {e}", exc_info=True)
            raise ConnectionError(f"Failed to connect to MongoDB: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        logger.info(f"[connection] Disconnecting (current state={self._state.value})")
        if self._client:
            await self._client.close()
        self._client = None
        self._state = ConnectionState.DISCONNECTED
        self._error = None
        logger.info("[connection] Disconnected")

    def get_client(self) -> MongoDBClient:
        """Get the active MongoDB client. Raises if not connected."""
        if self._state != ConnectionState.CONNECTED or not self._client:
            logger.error(f"[connection] get_client() called but state={self._state.value}")
            raise ConnectionError(
                f"MongoDB is not connected (state: {self._state.value}). "
                "Use the connect tool first."
            )
        return self._client


# Singleton — shared across all tools
connection_manager = ConnectionManager()