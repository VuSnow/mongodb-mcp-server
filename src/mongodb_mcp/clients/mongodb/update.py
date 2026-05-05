"""Update operations: update documents, rename collections."""
from __future__ import annotations
from typing import Any
from pymongo.results import UpdateResult
from .base import BaseMongoClient

class UpdateClient(BaseMongoClient):
    """Mixin for all update/modify operations."""

    async def update_one(self, database: str, collection: str, filter: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> UpdateResult:
        """Update a single document matching the filter."""
        col = self._client[database][collection]
        return await col.update_one(filter, update, upsert=upsert)

    async def update_many(self, database: str, collection: str, filter: dict[str, Any], update: dict[str, Any], upsert: bool = False) -> UpdateResult:
        """Update all documents matching the filter."""
        col = self._client[database][collection]
        return await col.update_many(filter, update, upsert=upsert)

    async def rename_collection(self, database: str, collection: str, new_name: str, drop_target: bool = False) -> None:
        """Rename a collection. Optionally drop the target if it already exists."""
        col = self._client[database][collection]
        await col.rename(new_name, dropTarget=drop_target)
