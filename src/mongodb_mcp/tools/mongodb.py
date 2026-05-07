import json
import logging

from mongodb_mcp.server import mcp
from mongodb_mcp.services.mongodb import mongodb_service

logger = logging.getLogger(__name__)


def _format_not_found(result: dict) -> str:
    """Format a not_found response with suggestions for user to confirm."""
    label = result["label"]
    name = result["name"]
    suggestions = result.get("suggestions", [])
    msg = f'{label} "{name}" not found.'
    if suggestions:
        msg += "\nDid you mean one of these?\n"
        msg += "\n".join(f"  - {s}" for s in suggestions)
        msg += "\nPlease confirm the correct name and try again."
    return msg


@mcp.tool()
async def list_databases() -> str:
    """List all databases with name and size in bytes."""
    logger.info("[tool:list_databases] Called")
    try:
        result = await mongodb_service.list_databases()
        databases = result["databases"]
        logger.info("[tool:list_databases] Returning %d databases", len(databases))
        return f"Found {len(databases)} databases:\n{json.dumps(databases, indent=2)}"
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:list_databases] %s", e)
        return f"Error: {e}"


@mcp.tool()
async def list_collections(database: str) -> str:
    """List all collections for a given database."""
    logger.info("[tool:list_collections] Called with db='%s'", database)
    try:
        result = await mongodb_service.list_collections(database)
        collections = result["collections"]
        if not collections:
            logger.info("[tool:list_collections] db='%s' has 0 collections", database)
            return f'Found 0 collections in "{database}".'
        logger.info("[tool:list_collections] db='%s' has %d collections", database, len(collections))
        return f'Found {len(collections)} collections in "{database}":\n{json.dumps(collections, indent=2)}'
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:list_collections] db='%s' — %s", database, e)
        return f"Error: {e}"


@mcp.tool()
async def collection_schema(database: str, collection: str, sample_size: int = 20) -> str:
    """Infer collection schema by sampling documents."""
    logger.info("[tool:collection_schema] Called with db='%s', col='%s', sample_size=%d", database, collection, sample_size)
    try:
        result = await mongodb_service.collection_schema(database, collection, sample_size)

        if result["status"] == "not_found":
            logger.info("[tool:collection_schema] Not found — returning suggestions")
            return _format_not_found(result)

        documents = result["documents"]
        if not documents:
            logger.info("[tool:collection_schema] %s.%s is empty", database, collection)
            return f"Collection {database}.{collection} exists but is empty."
        logger.info("[tool:collection_schema] Returning %d sampled documents", len(documents))
        return f"Sampled {len(documents)} documents from {database}.{collection}:\n{json.dumps(documents, indent=2, default=str)}"
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:collection_schema] %s.%s — %s", database, collection, e)
        return f"Error: {e}"


@mcp.tool()
async def collection_indexes(database: str, collection: str) -> str:
    """List all indexes for a collection."""
    logger.info("[tool:collection_indexes] Called with db='%s', col='%s'", database, collection)
    try:
        result = await mongodb_service.collection_indexes(database, collection)

        if result["status"] == "not_found":
            logger.info("[tool:collection_indexes] Not found — returning suggestions")
            return _format_not_found(result)

        indexes = result["indexes"]
        if not indexes:
            logger.info("[tool:collection_indexes] %s.%s has no indexes", database, collection)
            return f"No indexes found on {database}.{collection}."
        logger.info("[tool:collection_indexes] Returning %d indexes", len(indexes))
        return f"Found {len(indexes)} indexes on {database}.{collection}:\n{json.dumps(indexes, indent=2, default=str)}"
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:collection_indexes] %s.%s — %s", database, collection, e)
        return f"Error: {e}"


@mcp.tool()
async def db_stats(database: str) -> str:
    """Get statistics for a database (document count, storage size, indexes)."""
    logger.info("[tool:db_stats] Called with db='%s'", database)
    try:
        result = await mongodb_service.db_stats(database)

        if result["status"] == "not_found":
            logger.info("[tool:db_stats] Not found — returning suggestions")
            return _format_not_found(result)

        stats = result["stats"]
        logger.info("[tool:db_stats] Returning stats for db='%s'", database)
        return f"Stats for {database}:\n{json.dumps(stats, indent=2, default=str)}"
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:db_stats] db='%s' — %s", database, e)
        return f"Error: {e}"


@mcp.tool()
async def explain_query(
    database: str,
    collection: str,
    method: str,
    args: str,
    verbosity: str = "queryPlanner",
) -> str:
    """Explain a query plan. method: find|aggregate|count. args: JSON string of method arguments."""
    logger.info("[tool:explain_query] Called with db='%s', col='%s', method='%s', verbosity='%s'", database, collection, method, verbosity)
    try:
        parsed_args = json.loads(args)
    except json.JSONDecodeError as e:
        logger.warning("[tool:explain_query] Invalid JSON args: %s", e)
        return "Error: args must be a valid JSON string."

    try:
        result = await mongodb_service.explain(database, collection, method, parsed_args, verbosity)

        if result["status"] == "not_found":
            logger.info("[tool:explain_query] Not found — returning suggestions")
            return _format_not_found(result)
        if result["status"] == "error":
            logger.warning("[tool:explain_query] Service error: %s", result["message"])
            return f"Error: {result['message']}"

        plan = result["plan"]
        logger.info("[tool:explain_query] Returning explain plan for %s.%s", database, collection)
        return f"Explain ({method}, {verbosity}):\n{json.dumps(plan, indent=2, default=str)}"
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:explain_query] %s.%s — %s", database, collection, e)
        return f"Error: {e}"


@mcp.tool()
async def get_logs(log_type: str = "global", limit: int = 50) -> str:
    """Get recent MongoDB server log entries. log_type: global|startupWarnings."""
    logger.info("[tool:get_logs] Called with type='%s', limit=%d", log_type, limit)
    try:
        result = await mongodb_service.get_logs(log_type, limit)

        if result["status"] == "error":
            logger.warning("[tool:get_logs] Service error: %s", result["message"])
            return f"Error: {result['message']}"

        logs = result.get("logs", [])
        total = result.get("total_lines_written", 0)
        logger.info("[tool:get_logs] Returning %d of %d total lines", len(logs), total)
        return f"Showing {len(logs)} of {total} total log lines:\n" + "\n".join(logs)
    except (ConnectionError, ValueError) as e:
        logger.error("[tool:get_logs] %s", e)
        return f"Error: {e}"
