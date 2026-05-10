"""Metadata tools: list databases/collections, schema, indexes, stats, explain, logs."""
import json
import logging

from mongodb_mcp.app import mcp
from mongodb_mcp.services.mongodb import mongodb_service

from ._utils import _format_not_found

logger = logging.getLogger(__name__)


@mcp.tool()
async def list_databases() -> dict:
    """List all databases with name and size in bytes."""
    logger.info("[tool:list_databases] Called")
    try:
        result = await mongodb_service.list_databases()
        databases = result["databases"]
        logger.info(f"[tool:list_databases] Returning {len(databases)} databases")
        return {"result": f"Found {len(databases)} databases:\n{json.dumps(databases, indent=2)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:list_databases] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def list_collections(database: str) -> dict:
    """List all collections for a given database."""
    logger.info(f"[tool:list_collections] Called with db='{database}'")
    try:
        result = await mongodb_service.list_collections(database)
        collections = result["collections"]
        if not collections:
            logger.info(f"[tool:list_collections] db='{database}' has 0 collections")
            return {"result": f'Found 0 collections in "{database}".'}
        logger.info(f"[tool:list_collections] db='{database}' has {len(collections)} collections")
        return {"result": f'Found {len(collections)} collections in "{database}":\n{json.dumps(collections, indent=2)}'}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:list_collections] db='{database}' — {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def collection_schema(database: str, collection: str, sample_size: int = 20) -> dict:
    """Infer collection schema by sampling documents."""
    logger.info(f"[tool:collection_schema] Called with db='{database}', col='{collection}', sample_size={sample_size}")
    try:
        result = await mongodb_service.collection_schema(database, collection, sample_size)

        if result["status"] == "not_found":
            logger.info("[tool:collection_schema] Not found — returning suggestions")
            return {"result": _format_not_found(result)}

        documents = result["documents"]
        if not documents:
            logger.info(f"[tool:collection_schema] {database}.{collection} is empty")
            return {"result": f"Collection {database}.{collection} exists but is empty."}
        logger.info(f"[tool:collection_schema] Returning {len(documents)} sampled documents")
        return {"result": f"Sampled {len(documents)} documents from {database}.{collection}:\n{json.dumps(documents, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:collection_schema] {database}.{collection} — {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def collection_indexes(database: str, collection: str) -> dict:
    """List all indexes for a collection."""
    logger.info(f"[tool:collection_indexes] Called with db='{database}', col='{collection}'")
    try:
        result = await mongodb_service.collection_indexes(database, collection)

        if result["status"] == "not_found":
            logger.info("[tool:collection_indexes] Not found — returning suggestions")
            return {"result": _format_not_found(result)}

        indexes = result["indexes"]
        if not indexes:
            logger.info(f"[tool:collection_indexes] {database}.{collection} has no indexes")
            return {"result": f"No indexes found on {database}.{collection}."}
        logger.info(f"[tool:collection_indexes] Returning {len(indexes)} indexes")
        return {"result": f"Found {len(indexes)} indexes on {database}.{collection}:\n{json.dumps(indexes, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:collection_indexes] {database}.{collection} — {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def db_stats(database: str) -> dict:
    """Get statistics for a database (document count, storage size, indexes)."""
    logger.info(f"[tool:db_stats] Called with db='{database}'")
    try:
        result = await mongodb_service.db_stats(database)

        if result["status"] == "not_found":
            logger.info("[tool:db_stats] Not found — returning suggestions")
            return {"result": _format_not_found(result)}

        stats = result["stats"]
        logger.info(f"[tool:db_stats] Returning stats for db='{database}'")
        return {"result": f"Stats for {database}:\n{json.dumps(stats, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:db_stats] db='{database}' — {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def explain_query(
    database: str,
    collection: str,
    method: str,
    args: str,
    verbosity: str = "queryPlanner",
) -> dict:
    """Explain a query plan. method: find|aggregate|count. args: JSON string of method arguments."""
    logger.info(f"[tool:explain_query] Called with db='{database}', col='{collection}', method='{method}', verbosity='{verbosity}'")
    try:
        parsed_args = json.loads(args)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:explain_query] Invalid JSON args: {e}")
        return {"result": "Error: args must be a valid JSON string."}

    try:
        result = await mongodb_service.explain(database, collection, method, parsed_args, verbosity)

        if result["status"] == "not_found":
            logger.info("[tool:explain_query] Not found — returning suggestions")
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            logger.warning(f"[tool:explain_query] Service error: {result['message']}")
            return {"result": f"Error: {result['message']}"}

        plan = result["plan"]
        logger.info(f"[tool:explain_query] Returning explain plan for {database}.{collection}")
        return {"result": f"Explain ({method}, {verbosity}):\n{json.dumps(plan, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:explain_query] {database}.{collection} — {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def get_logs(log_type: str = "global", limit: int = 50) -> dict:
    """Get recent MongoDB server log entries. log_type: global|startupWarnings."""
    logger.info(f"[tool:get_logs] Called with type='{log_type}', limit={limit}")
    try:
        result = await mongodb_service.get_logs(log_type, limit)

        if result["status"] == "error":
            logger.warning(f"[tool:get_logs] Service error: {result['message']}")
            return {"result": f"Error: {result['message']}"}

        logs = result.get("logs", [])
        total = result.get("total_lines_written", 0)
        logger.info(f"[tool:get_logs] Returning {len(logs)} of {total} total lines")
        return {"result": f"Showing {len(logs)} of {total} total log lines:\n" + "\n".join(logs)}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:get_logs] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def collection_stats(
    database: str,
    collection: str,
) -> dict:
    """Get storage statistics for a collection (document count, storage size, avg object size, index sizes)."""
    logger.info(f"[tool:collection_stats] Called with db='{database}', col='{collection}'")
    try:
        result = await mongodb_service.collection_stats(database, collection)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}

        stats = result["stats"]
        if not stats:
            return {"result": f"No storage stats available for {database}.{collection}."}

        summary = {
            "count": stats.get("count", "N/A"),
            "size": stats.get("size", "N/A"),
            "avgObjSize": stats.get("avgObjSize", "N/A"),
            "storageSize": stats.get("storageSize", "N/A"),
            "totalIndexSize": stats.get("totalIndexSize", "N/A"),
            "nindexes": stats.get("nindexes", "N/A"),
        }
        logger.info(f"[tool:collection_stats] Success for {database}.{collection}")
        return {"result": f"Storage stats for {database}.{collection}:\n{json.dumps(summary, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:collection_stats] {e}")
        return {"result": f"Error: {e}"}
