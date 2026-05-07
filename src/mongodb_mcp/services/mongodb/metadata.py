from typing import Any, List, Dict
from .base import BaseMongoDBService

import logging

logger = logging.getLogger(__name__)


class MetadataService(BaseMongoDBService):
    """Service for metadata operations. Lazy resolve: only resolve on empty/error."""

    async def _get_db_names(self) -> List[str]:
        """Fetch flat list of database names."""
        client = await self._ensure_connected()
        dbs = await client.list_database_names()
        return [d["name"] for d in dbs]

    async def _resolve_db_and_collection(self, database: str, collection: str) -> Dict[str, Any] | None:
        """Resolve DB then collection. Returns not_found dict or None if both exist."""
        logger.info("[resolve] Checking existence of db='%s', collection='%s'", database, collection)
        client = await self._ensure_connected()

        db_result = await self._resolve_name(database, self._get_db_names)
        if not db_result.found:
            logger.warning("[resolve] Database '%s' not found — suggesting alternatives", database)
            return {
                "status": "not_found",
                "label": "Database",
                "name": db_result.name,
                "suggestions": db_result.suggestions,
            }

        col_result = await self._resolve_name(
            collection,
            lambda: client.list_collection_names(database),
        )
        if not col_result.found:
            logger.warning("[resolve] Collection '%s' not found in db='%s' — suggesting alternatives", collection, database)
            return {
                "status": "not_found",
                "label": "Collection",
                "name": col_result.name,
                "suggestions": col_result.suggestions,
            }

        logger.debug("[resolve] Both db='%s' and collection='%s' exist", database, collection)
        return None

    # ── No resolve ──

    async def list_databases(self) -> dict[str, Any]:
        logger.info("[list_databases] Fetching all databases")
        client = await self._ensure_connected()
        databases = await client.list_database_names()
        logger.info("[list_databases] Found %d databases", len(databases))
        return {"status": "ok", "databases": databases}

    async def list_collections(self, database: str) -> dict[str, Any]:
        logger.info("[list_collections] db='%s'", database)
        self._validate_name(database, "Database name")
        client = await self._ensure_connected()
        collections = await client.list_collection_names(database)
        logger.info("[list_collections] db='%s' — found %d collections", database, len(collections))
        return {"status": "ok", "database": database, "collections": collections}

    async def get_logs(self, log_type: str = "global", limit: int = 50) -> dict[str, Any]:
        logger.info("[get_logs] type='%s', limit=%d", log_type, limit)
        if log_type not in ("global", "startupWarnings"):
            logger.warning("[get_logs] Invalid log_type='%s'", log_type)
            return {
                "status": "error",
                "message": f"Invalid log_type: {log_type}. Use: global, startupWarnings",
            }
        limit = max(1, min(limit, 1000))
        client = await self._ensure_connected()
        logs = await client.get_logs(log_type, limit)
        logger.info("[get_logs] Returned %d log lines", len(logs.get("logs", [])))
        return {"status": "ok", **logs}

    # ── Lazy resolve on empty/error ──

    async def collection_schema(self, database: str, collection: str, sample_size: int = 20) -> Dict[str, Any]:
        logger.info("[collection_schema] db='%s', collection='%s', sample_size=%d", database, collection, sample_size)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        sample_size = max(1, min(sample_size, 100))
        client = await self._ensure_connected()

        documents = await client.collection_schema(
            database=database,
            collection=collection,
            sample_size=sample_size,
        )

        if not documents:
            logger.info("[collection_schema] Empty result for %s.%s — triggering resolve", database, collection)
            not_found = await self._resolve_db_and_collection(database=database, collection=collection)
            if not_found:
                return not_found
            logger.info("[collection_schema] %s.%s exists but is genuinely empty", database, collection)
            return {"status": "ok", "documents": []}

        logger.info("[collection_schema] Returned %d documents from %s.%s", len(documents), database, collection)
        return {"status": "ok", "documents": documents}

    async def collection_indexes(self, database: str, collection: str) -> Dict[str, Any]:
        logger.info("[collection_indexes] db='%s', collection='%s'", database, collection)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")
        client = await self._ensure_connected()

        indexes = await client.collection_indexes(database=database, collection=collection)

        if not indexes:
            logger.info("[collection_indexes] Empty result for %s.%s — triggering resolve", database, collection)
            not_found = await self._resolve_db_and_collection(database=database, collection=collection)
            if not_found:
                return not_found
            logger.info("[collection_indexes] %s.%s exists but has no indexes", database, collection)
            return {"status": "ok", "indexes": []}

        logger.info("[collection_indexes] Found %d indexes on %s.%s", len(indexes), database, collection)
        return {"status": "ok", "indexes": indexes}

    async def db_stats(self, database: str) -> Dict[str, Any]:
        logger.info("[db_stats] db='%s'", database)
        self._validate_name(database, "Database name")
        client = await self._ensure_connected()

        try:
            stats = await client.db_stats(database)
        except Exception as e:
            logger.error("[db_stats] Exception for db='%s': %s", database, e, exc_info=True)
            db_result = await self._resolve_name(database, self._get_db_names)
            if not db_result.found:
                logger.warning("[db_stats] Database '%s' does not exist — returning suggestions", database)
                return {
                    "status": "not_found",
                    "label": "Database",
                    "name": db_result.name,
                    "suggestions": db_result.suggestions,
                }
            # DB exists but unknown error — re-raise
            raise

        logger.info("[db_stats] Success for db='%s'", database)
        return {"status": "ok", "stats": stats}

    async def explain(self, database: str, collection: str, method: str, args: Dict[str, Any], verbosity: str = "queryPlanner") -> Dict[str, Any]:
        logger.info("[explain] db='%s', collection='%s', method='%s', verbosity='%s'", database, collection, method, verbosity)
        self._validate_name(database, "Database name")
        self._validate_name(collection, "Collection name")

        if method not in ("find", "aggregate", "count"):
            logger.warning("[explain] Invalid method='%s'", method)
            return {
                "status": "error",
                "message": f"Unsupported method: {method}. Use: find, aggregate, count",
            }

        if verbosity not in ("queryPlanner", "queryPlannerExtended", "executionStats", "allPlansExecution"):
            logger.warning("[explain] Invalid verbosity='%s'", verbosity)
            return {
                "status": "error",
                "message": f"Unsupported verbosity: {verbosity}. Use: queryPlanner, executionStats, allPlansExecution",
            }

        client = await self._ensure_connected()

        try:
            plan = await client.explain(
                database=database,
                collection=collection,
                args=args,
                method=method,
                verbosity=verbosity,
            )
        except Exception as e:
            logger.error("[explain] Exception for %s.%s method='%s': %s", database, collection, method, e, exc_info=True)
            not_found = await self._resolve_db_and_collection(database, collection)
            if not_found:
                return not_found
            # Names exist but unknown error — re-raise
            raise

        logger.info("[explain] Success for %s.%s method='%s'", database, collection, method)
        return {"status": "ok", "plan": plan}
