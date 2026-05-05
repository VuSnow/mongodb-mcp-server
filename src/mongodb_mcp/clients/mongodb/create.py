"""Create operations: insert documents, create collections and indexes."""
from __future__ import annotations
from typing import Any
from pymongo.results import InsertOneResult, InsertManyResult
from .base import BaseMongoClient

class CreateClient(BaseMongoClient):
    """Mixin for all create/insert operations."""

    async def insert_one(self, database: str, collection: str, document: dict[str, Any]) -> InsertOneResult:
        """Insert a single document into a collection."""
        col = self._client[database][collection]
        return await col.insert_one(document)

    async def insert_many(self, database: str, collection: str, documents: list[dict[str, Any]], ordered: bool = False) -> InsertManyResult:
        """Insert multiple documents into a collection."""
        col = self._client[database][collection]
        return await col.insert_many(documents, ordered=ordered)

    async def create_collection(self, database: str, collection: str) -> None:
        """Create a new collection. Database is created automatically if it doesn't exist."""
        db = self._client[database]
        await db.create_collection(collection)

    async def create_index(self, database: str, collection: str, keys: list[tuple[str, int]], unique: bool = False, name: str | None = None) -> str:
        """Create a classic index on a collection. Returns the index name."""
        col = self._client[database][collection]
        kwargs: dict[str, Any] = {"unique": unique}
        if name:
            kwargs["name"] = name
        return await col.create_index(keys, **kwargs)

    async def create_vector_search_index(self, database: str, collection: str, index_name: str, definition: dict[str, Any]) -> str:
        """Create a vector search index on a collection."""
        col = self._client[database][collection]
        from pymongo.operations import SearchIndexModel

        model = SearchIndexModel(
            definition=definition,
            name=index_name,
            type="vectorSearch",
        )
        return await col.create_search_index(model)
