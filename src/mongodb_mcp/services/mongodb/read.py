"""Read operations service: find, aggregate, count."""
from typing import Any, Dict, List

from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class ReadService(BaseMongoDBService):
    """Service for read/query operations. Validates input and lazy-resolves names."""

    async def find(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any] | None = None,
        projection: Dict[str, Any] | None = None,
        sort: List[List] | None = None,
        skip: int = 0,
        limit: int = 10,
    ) -> Dict[str, Any]:
        logger.info(f"[find] db='{database}', collection='{collection}', skip={skip}, limit={limit}")
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        limit = max(1, min(limit, 1000))
        skip = max(0, skip)

        # Convert [[field, direction], ...] to [(field, direction), ...]
        sort_tuples = None
        if sort:
            try:
                sort_tuples = [(s[0], int(s[1])) for s in sort]
            except (IndexError, ValueError, TypeError):
                return {"status": "error", "message": "Each sort item must be [field_name, direction]. Direction: 1 (asc) or -1 (desc)."}

        client = await self._ensure_connected()

        try:
            documents = await client.find(
                database, collection,
                filter=filter, projection=projection,
                sort=sort_tuples, skip=skip, limit=limit,
            )
        except Exception as e:
            logger.error(f"[find] Exception for {database}.{collection}: {e}", exc_info=True)
            # Lazy resolve on error
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            raise

        if not documents:
            logger.info(f"[find] Empty result for {database}.{collection} — triggering resolve")
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            logger.info(f"[find] {database}.{collection} exists but query returned 0 results")
            return {"status": "ok", "documents": [], "count": 0}

        logger.info(f"[find] Returned {len(documents)} documents from {database}.{collection}")
        return {"status": "ok", "documents": documents, "count": len(documents)}

    async def aggregate(
        self,
        database: str,
        collection: str,
        pipeline: List[Dict[str, Any]],
        limit: int = 1000,
    ) -> Dict[str, Any]:
        logger.info(f"[aggregate] db='{database}', collection='{collection}', stages={len(pipeline)}, limit={limit}")
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        limit = max(1, min(limit, 10000))

        if not pipeline or not isinstance(pipeline, list):
            return {"status": "error", "message": "Pipeline must be a non-empty list of stage objects."}

        for i, stage in enumerate(pipeline):
            if not isinstance(stage, dict):
                return {"status": "error", "message": f"Pipeline stage at index {i} is not a JSON object."}

        client = await self._ensure_connected()

        try:
            results = await client.aggregate(database, collection, pipeline, limit=limit)
        except Exception as e:
            logger.error(f"[aggregate] Exception for {database}.{collection}: {e}", exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            raise

        logger.info(f"[aggregate] Returned {len(results)} results from {database}.{collection}")
        return {"status": "ok", "results": results, "count": len(results)}

    async def count_documents(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        logger.info(f"[count_documents] db='{database}', collection='{collection}'")
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        client = await self._ensure_connected()

        try:
            count = await client.count_documents(database, collection, filter=filter)
        except Exception as e:
            logger.error(f"[count_documents] Exception for {database}.{collection}: {e}", exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            raise

        logger.info(f"[count_documents] {database}.{collection} has {count} documents")
        return {"status": "ok", "count": count}

    async def distinct(
        self,
        database: str,
        collection: str,
        field: str,
        filter: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        logger.info(f"[distinct] db='{database}', collection='{collection}', field='{field}'")
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        if not field or not field.strip():
            return {"status": "error", "message": "field is required and cannot be empty."}

        client = await self._ensure_connected()

        try:
            values = await client.distinct(database, collection, field, filter=filter)
        except Exception as e:
            logger.error(f"[distinct] Exception for {database}.{collection}.{field}: {e}", exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            raise

        logger.info(f"[distinct] {database}.{collection}.{field} has {len(values)} distinct values")
        return {"status": "ok", "field": field, "values": values, "count": len(values)}