"""Update operations service: update documents, rename collections."""
from typing import Any, Dict, List

from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class UpdateService(BaseMongoDBService):
    """Service for update operations. Enforces write policy and validates input."""

    async def update_one(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> Dict[str, Any]:
        logger.info(f"[update_one] db='{database}', collection='{collection}', upsert={upsert}")
        self._check_write_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not filter or not isinstance(filter, dict):
            return {"status": "error", "message": "filter must be a non-empty JSON object."}
        if not update or not isinstance(update, dict):
            return {"status": "error", "message": "update must be a non-empty JSON object."}

        # Validate update operators
        valid = self._validate_update_operators(update)
        if valid is not None:
            return valid

        client = await self._ensure_connected()

        try:
            result = await client.update_one(database, collection, filter, update, upsert=upsert)
        except Exception as e:
            logger.error(f"[update_one] Exception for {database}.{collection}: {e}", exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            return {"status": "error", "message": str(e)}

        logger.info(f"[update_one] matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
        return {
            "status": "ok",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None,
        }

    async def update_many(
        self,
        database: str,
        collection: str,
        filter: Dict[str, Any],
        update: Dict[str, Any],
        upsert: bool = False,
    ) -> Dict[str, Any]:
        logger.info(f"[update_many] db='{database}', collection='{collection}', upsert={upsert}")
        self._check_write_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if not filter or not isinstance(filter, dict):
            return {"status": "error", "message": "filter must be a non-empty JSON object."}
        if not update or not isinstance(update, dict):
            return {"status": "error", "message": "update must be a non-empty JSON object."}

        valid = self._validate_update_operators(update)
        if valid is not None:
            return valid

        client = await self._ensure_connected()

        try:
            result = await client.update_many(database, collection, filter, update, upsert=upsert)
        except Exception as e:
            logger.error(f"[update_many] Exception for {database}.{collection}: {e}", exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            return {"status": "error", "message": str(e)}

        logger.info(f"[update_many] matched={result.matched_count}, modified={result.modified_count}, upserted_id={result.upserted_id}")
        return {
            "status": "ok",
            "matched_count": result.matched_count,
            "modified_count": result.modified_count,
            "upserted_id": str(result.upserted_id) if result.upserted_id else None,
        }

    async def rename_collection(
        self,
        database: str,
        collection: str,
        new_name: str,
        drop_target: bool = False,
    ) -> Dict[str, Any]:
        logger.info(f"[rename_collection] db='{database}', collection='{collection}' -> '{new_name}', drop_target={drop_target}")
        self._check_write_allowed()
        self._check_write_target(database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        self._validate_name(new_name, "New collection name")

        if collection == new_name:
            return {"status": "error", "message": "New name must be different from the current name."}

        client = await self._ensure_connected()

        # Verify source collection exists
        existing = await client.list_collection_names(database)
        if collection not in existing:
            not_found = await self._resolve_name(collection, lambda: client.list_collection_names(database))
            if not not_found.found:
                return {
                    "status": "not_found",
                    "label": "Collection",
                    "name": not_found.name,
                    "suggestions": not_found.suggestions,
                }

        # Check target doesn't already exist (unless drop_target=True)
        if not drop_target and new_name in existing:
            return {"status": "error", "message": f"Target collection '{new_name}' already exists. Set drop_target=true to overwrite."}

        try:
            await client.rename_collection(database, collection, new_name, drop_target=drop_target)
        except Exception as e:
            logger.error(f"[rename_collection] Exception: {e}", exc_info=True)
            return {"status": "error", "message": str(e)}

        logger.info(f"[rename_collection] Renamed {database}.{collection} -> {database}.{new_name}")
        return {"status": "ok", "database": database, "old_name": collection, "new_name": new_name}

    @staticmethod
    def _validate_update_operators(update: Dict[str, Any]) -> Dict[str, Any] | None:
        """Validate that update uses operators ($set, $inc, etc.), not raw replacement."""
        valid_operators = {
            "$set", "$unset", "$inc", "$mul", "$min", "$max",
            "$rename", "$push", "$pull", "$addToSet", "$pop",
            "$currentDate", "$bit", "$setOnInsert",
        }
        keys = set(update.keys())
        if not keys:
            return {"status": "error", "message": "update object cannot be empty."}

        # All keys must start with $ (be operators)
        non_operators = [k for k in keys if not k.startswith("$")]
        if non_operators:
            return {
                "status": "error",
                "message": f"update must use operators (e.g. $set, $inc). "
                           f"Found non-operator keys: {non_operators}. "
                           f"Example: {{\"$set\": {{\"name\": \"Alice\"}}}}",
            }

        unknown = keys - valid_operators
        if unknown:
            return {
                "status": "error",
                "message": f"Unknown update operators: {list(unknown)}. "
                           f"Supported: {sorted(valid_operators)}",
            }

        return None
