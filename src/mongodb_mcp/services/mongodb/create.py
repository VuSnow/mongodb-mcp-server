"""Create operations service: insert documents, create collections and indexes."""
from typing import Any, Dict, List

from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class CreateService(BaseMongoDBService):
    """Service for create operations. Enforces write policy and validates input."""

    async def insert_one(self, database: str, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("[insert_one] db='%s', collection='%s'", database, collection)
        self._check_write_allowed()
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not document or not isinstance(document, dict):
            logger.warning("[insert_one] Invalid document: must be a non-empty dict")
            return {"status": "error", "message": "Document must be a non-empty JSON object."}

        client = await self._ensure_connected()

        try:
            result = await client.insert_one(database, collection, document)
        except Exception as e:
            logger.error("[insert_one] Exception for %s.%s: %s", database, collection, e, exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info("[insert_one] Inserted id=%s into %s.%s", result.inserted_id, database, collection)
        return {"status": "ok", "inserted_id": str(result.inserted_id)}

    async def insert_many(
        self, database: str, collection: str, documents: List[Dict[str, Any]], ordered: bool = False,
    ) -> Dict[str, Any]:
        logger.info("[insert_many] db='%s', collection='%s', count=%d, ordered=%s", database, collection, len(documents), ordered)
        self._check_write_allowed()
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not documents or not isinstance(documents, list):
            logger.warning("[insert_many] Invalid documents: must be a non-empty list")
            return {"status": "error", "message": "Documents must be a non-empty list of JSON objects."}

        for i, doc in enumerate(documents):
            if not isinstance(doc, dict):
                return {"status": "error", "message": f"Item at index {i} is not a JSON object."}

        client = await self._ensure_connected()

        try:
            result = await client.insert_many(database, collection, documents, ordered=ordered)
        except Exception as e:
            logger.error("[insert_many] Exception for %s.%s: %s", database, collection, e, exc_info=True)
            return {"status": "error", "message": str(e)}

        inserted_ids = [str(id_) for id_ in result.inserted_ids]
        logger.info("[insert_many] Inserted %d documents into %s.%s", len(inserted_ids), database, collection)
        return {"status": "ok", "inserted_count": len(inserted_ids), "inserted_ids": inserted_ids}

    async def create_collection(self, database: str, collection: str) -> Dict[str, Any]:
        logger.info("[create_collection] db='%s', collection='%s'", database, collection)
        self._check_write_allowed()
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        client = await self._ensure_connected()

        # Check if collection already exists
        existing = await client.list_collection_names(database)
        if collection in existing:
            logger.warning("[create_collection] Collection '%s' already exists in db='%s'", collection, database)
            return {"status": "error", "message": f"Collection '{collection}' already exists in database '{database}'."}

        try:
            await client.create_collection(database, collection)
        except Exception as e:
            logger.error("[create_collection] Exception: %s", e, exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info("[create_collection] Created %s.%s", database, collection)
        return {"status": "ok", "database": database, "collection": collection}

    async def create_index(
        self,
        database: str,
        collection: str,
        keys: List[List],
        unique: bool = False,
        name: str | None = None,
    ) -> Dict[str, Any]:
        logger.info("[create_index] db='%s', collection='%s', keys=%s, unique=%s", database, collection, keys, unique)
        self._check_write_allowed()
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not keys or not isinstance(keys, list):
            return {"status": "error", "message": "Keys must be a non-empty list of [field, direction] pairs."}

        # Convert [[field, direction], ...] to [(field, direction), ...]
        try:
            key_tuples = [(k[0], int(k[1])) for k in keys]
        except (IndexError, ValueError, TypeError):
            return {"status": "error", "message": "Each key must be [field_name, direction]. Direction: 1 (asc) or -1 (desc)."}

        client = await self._ensure_connected()

        # Verify collection exists
        existing = await client.list_collection_names(database)
        if collection not in existing:
            not_found = await self._resolve_name(collection, lambda: client.list_collection_names(database))
            if not not_found.found:
                logger.warning("[create_index] Collection '%s' not found in db='%s'", collection, database)
                return {
                    "status": "not_found",
                    "label": "Collection",
                    "name": not_found.name,
                    "suggestions": not_found.suggestions,
                }

        try:
            index_name = await client.create_index(database, collection, key_tuples, unique=unique, name=name)
        except Exception as e:
            logger.error("[create_index] Exception: %s", e, exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info("[create_index] Created index '%s' on %s.%s", index_name, database, collection)
        return {"status": "ok", "index_name": index_name, "database": database, "collection": collection}
