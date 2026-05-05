from __future__ import annotations
from pymongo import AsyncMongoClient

class BaseMongoClient:
    """Holds the shared AsyncMongoClient instance."""

    def __init__(self, connection_string: str, timeout_ms: int = 30000) -> None:
        self._client = AsyncMongoClient(
            connection_string,
            serverSelectionTimeoutMS=timeout_ms,
        )

    async def ping(self) -> bool:
        await self._client.admin.command("ping")
        return True

    async def close(self) -> None:
        self._client.close()
