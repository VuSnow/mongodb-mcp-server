"""Create operations service: insert documents, create collections and indexes."""
from typing import Any, Dict, List

from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class CreateService(BaseMongoDBService):
    """Service for create operations. Enforces write policy and validates input."""

    async def insert_one(self, database: str, collection: str, document: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[insert_one] db='{database}', collection='{collection}'")
        self._check_write_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not document or not isinstance(document, dict):
            logger.warning("[insert_one] Invalid document: must be a non-empty dict")
            return {"status": "error", "message": "Document must be a non-empty JSON object."}

        client = await self._ensure_connected()

        try:
            result = await client.insert_one(database, collection, document)
        except Exception as e:
            logger.error(f"[insert_one] Exception for {database}.{collection}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[insert_one] Inserted id={result.inserted_id} into {database}.{collection}")
        return {"status": "ok", "inserted_id": str(result.inserted_id)}

    async def insert_many(
        self, database: str, collection: str, documents: List[Dict[str, Any]], ordered: bool = False,
    ) -> Dict[str, Any]:
        logger.info(f"[insert_many] db='{database}', collection='{collection}', count={len(documents)}, ordered={ordered}")
        self._check_write_allowed()
        self._check_write_target(database, collection)
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
            logger.error(f"[insert_many] Exception for {database}.{collection}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        inserted_ids = [str(id_) for id_ in result.inserted_ids]
        logger.info(f"[insert_many] Inserted {len(inserted_ids)} documents into {database}.{collection}")
        return {"status": "ok", "inserted_count": len(inserted_ids), "inserted_ids": inserted_ids}

    async def create_collection(self, database: str, collection: str) -> Dict[str, Any]:
        logger.info(f"[create_collection] db='{database}', collection='{collection}'")
        self._check_write_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        client = await self._ensure_connected()

        # Check if collection already exists
        existing = await client.list_collection_names(database)
        if collection in existing:
            logger.warning(f"[create_collection] Collection '{collection}' already exists in db='{database}'")
            return {"status": "error", "message": f"Collection '{collection}' already exists in database '{database}'."}

        try:
            await client.create_collection(database, collection)
        except Exception as e:
            logger.error(f"[create_collection] Exception: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[create_collection] Created {database}.{collection}")
        return {"status": "ok", "database": database, "collection": collection}

    async def create_index(
        self,
        database: str,
        collection: str,
        keys: List[List],
        unique: bool = False,
        name: str | None = None,
    ) -> Dict[str, Any]:
        logger.info(f"[create_index] db='{database}', collection='{collection}', keys={keys}, unique={unique}")
        self._check_write_allowed()
        self._check_write_target(database, collection)
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
                logger.warning(f"[create_index] Collection '{collection}' not found in db='{database}'")
                return {
                    "status": "not_found",
                    "label": "Collection",
                    "name": not_found.name,
                    "suggestions": not_found.suggestions,
                }

        try:
            index_name = await client.create_index(database, collection, key_tuples, unique=unique, name=name)
        except Exception as e:
            logger.error(f"[create_index] Exception: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[create_index] Created index '{index_name}' on {database}.{collection}")
        return {"status": "ok", "index_name": index_name, "database": database, "collection": collection}
