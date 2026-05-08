"""Delete operations service: delete documents, drop collections, databases, and indexes."""
from typing import Any, Dict

from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class DeleteService(BaseMongoDBService):
    """Service for delete/drop operations. Enforces destructive-write policy."""

    async def delete_one(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"[delete_one] db='{database}', collection='{collection}'")
        self._check_destructive_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not isinstance(filter, dict):
            return {"status": "error", "message": "filter must be a JSON object."}

        client = await self._ensure_connected()

        not_found = await self._resolve_db_and_collection(database, collection)
        if not_found:
            return not_found

        try:
            result = await client.delete_one(database, collection, filter)
        except Exception as e:
            logger.error(f"[delete_one] Exception for {database}.{collection}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[delete_one] deleted_count={result.deleted_count}")
        return {"status": "ok", "deleted_count": result.deleted_count}

    async def delete_many(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any],
    ) -> Dict[str, Any]:
        logger.info(f"[delete_many] db='{database}', collection='{collection}'")
        self._check_destructive_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not isinstance(filter, dict):
            return {"status": "error", "message": "filter must be a JSON object."}

        client = await self._ensure_connected()

        not_found = await self._resolve_db_and_collection(database, collection)
        if not_found:
            return not_found

        try:
            result = await client.delete_many(database, collection, filter)
        except Exception as e:
            logger.error(f"[delete_many] Exception for {database}.{collection}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[delete_many] deleted_count={result.deleted_count}")
        return {"status": "ok", "deleted_count": result.deleted_count}

    async def drop_collection(self, database: str, collection: str) -> Dict[str, Any]:
        logger.info(f"[drop_collection] db='{database}', collection='{collection}'")
        self._check_destructive_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        client = await self._ensure_connected()

        not_found = await self._resolve_db_and_collection(database, collection)
        if not_found:
            return not_found

        try:
            await client.drop_collection(database, collection)
        except Exception as e:
            logger.error(f"[drop_collection] Exception for {database}.{collection}: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[drop_collection] Dropped {database}.{collection}")
        return {"status": "ok"}

    async def drop_database(self, database: str) -> Dict[str, Any]:
        logger.info(f"[drop_database] db='{database}'")
        self._check_destructive_allowed()
        self._validate_name(database, "Database name")

        client = await self._ensure_connected()

        db_check = await self._resolve_name(database, self._get_db_names)
        if not db_check.found:
            return {
                "status": "not_found",
                "label": "Database",
                "name": database,
                "suggestions": db_check.suggestions,
            }

        try:
            await client.drop_database(database)
        except Exception as e:
            logger.error(f"[drop_database] Exception for db='{database}': {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[drop_database] Dropped database '{database}'")
        return {"status": "ok"}

    async def drop_index(self, database: str, collection: str, index_name: str) -> Dict[str, Any]:
        logger.info(f"[drop_index] db='{database}', collection='{collection}', index='{index_name}'")
        self._check_destructive_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not index_name or not index_name.strip():
            return {"status": "error", "message": "index_name must be a non-empty string."}

        client = await self._ensure_connected()

        not_found = await self._resolve_db_and_collection(database, collection)
        if not_found:
            return not_found

        try:
            await client.drop_index(database, collection, index_name)
        except Exception as e:
            logger.error(f"[drop_index] Exception for {database}.{collection}[{index_name}]: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[drop_index] Dropped index '{index_name}' on {database}.{collection}")
        return {"status": "ok"}
