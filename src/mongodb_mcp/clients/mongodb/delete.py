"""Delete operations: delete documents, drop collections, databases, and indexes."""
from __future__ import annotations
from typing import Any
from pymongo.results import DeleteResult
from .base import BaseMongoClient

class DeleteClient(BaseMongoClient):
    """Mixin for all delete/drop operations."""

    async def delete_one(self, database: str, collection: str, filter: dict[str, Any]) -> DeleteResult:
        """Delete a single document matching the filter."""
        col = self._client[database][collection]
        return await col.delete_one(filter)

    async def delete_many(self, database: str, collection: str, filter: dict[str, Any] | None = None) -> DeleteResult:
        """Delete all documents matching the filter."""
        col = self._client[database][collection]
        return await col.delete_many(filter or {})

    async def drop_collection(self, database: str, collection: str) -> bool:
        """Drop a collection and all its indexes. Returns True if successful."""
        db = self._client[database]
        await db.drop_collection(collection)
        return True

    async def drop_database(self, database: str) -> bool:
        """Drop an entire database. Returns True if successful."""
        await self._client.drop_database(database)
        return True

    async def drop_index(self, database: str, collection: str, index_name: str) -> bool:
        """Drop a classic index by name. Returns True if successful."""
        col = self._client[database][collection]
        await col.drop_index(index_name)
        return True