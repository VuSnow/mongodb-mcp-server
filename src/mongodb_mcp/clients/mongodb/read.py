"""Read operations: find, aggregate, count."""
from __future__ import annotations
from typing import Any
from .base import BaseMongoClient

class ReadClient(BaseMongoClient):
    """Mixin for all read/query operations."""

    async def find(self, database: str, collection: str, filter: dict[str, Any] | None = None, projection: dict[str, Any] | None = None, sort: list[tuple[str, int]] | None = None, skip: int = 0, limit: int = 10) -> list[dict[str, Any]]:
        """Run a find query against a collection."""
        col = self._client[database][collection]
        cursor = col.find(filter or {}, projection)
        if sort:
            cursor = cursor.sort(sort)
        if skip > 0:
            cursor = cursor.skip(skip)
        cursor = cursor.limit(limit)
        return await cursor.to_list(length=limit)

    async def aggregate(self, database: str, collection: str, pipeline: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
        """Run an aggregation pipeline against a collection."""
        col = self._client[database][collection]
        cursor = col.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def aggregate_db(self, database: str, pipeline: list[dict[str, Any]], limit: int = 1000) -> list[dict[str, Any]]:
        """Run a database-level aggregation (e.g. $currentOp, $listLocalSessions)."""
        db = self._client[database]
        cursor = db.aggregate(pipeline)
        return await cursor.to_list(length=limit)

    async def count_documents(self, database: str, collection: str, filter: dict[str, Any] | None = None) -> int:
        """Count documents matching a filter."""
        col = self._client[database][collection]
        return await col.count_documents(filter or {})
