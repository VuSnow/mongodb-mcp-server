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


# ── Create Tools ─────────────────────────────────────────────────────────────


@mcp.tool()
async def insert_one(database: str, collection: str, document: str) -> str:
    """Insert a single document into a collection. document: JSON string of the document to insert."""
    logger.info("[tool:insert_one] Called with db='%s', col='%s'", database, collection)
    try:
        parsed_doc = json.loads(document)
    except json.JSONDecodeError as e:
        logger.warning("[tool:insert_one] Invalid JSON document: %s", e)
        return "Error: document must be a valid JSON string."

    try:
        result = await mongodb_service.insert_one(database, collection, parsed_doc)

        if result["status"] == "error":
            return f"Error: {result['message']}"

        logger.info("[tool:insert_one] Inserted id=%s", result["inserted_id"])
        return f"Inserted 1 document into {database}.{collection}.\nInserted ID: {result['inserted_id']}"
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error("[tool:insert_one] %s", e)
        return f"Error: {e}"


@mcp.tool()
async def insert_many(database: str, collection: str, documents: str, ordered: bool = False) -> str:
    """Insert multiple documents into a collection. documents: JSON array of documents."""
    logger.info("[tool:insert_many] Called with db='%s', col='%s', ordered=%s", database, collection, ordered)
    try:
        parsed_docs = json.loads(documents)
    except json.JSONDecodeError as e:
        logger.warning("[tool:insert_many] Invalid JSON: %s", e)
        return "Error: documents must be a valid JSON array."

    if not isinstance(parsed_docs, list):
        return "Error: documents must be a JSON array of objects."

    try:
        result = await mongodb_service.insert_many(database, collection, parsed_docs, ordered=ordered)

        if result["status"] == "error":
            return f"Error: {result['message']}"

        count = result["inserted_count"]
        logger.info("[tool:insert_many] Inserted %d documents", count)
        return f"Inserted {count} documents into {database}.{collection}.\nInserted IDs: {json.dumps(result['inserted_ids'])}"
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error("[tool:insert_many] %s", e)
        return f"Error: {e}"


@mcp.tool()
async def create_collection(database: str, collection: str) -> str:
    """Create a new collection in a database."""
    logger.info("[tool:create_collection] Called with db='%s', col='%s'", database, collection)
    try:
        result = await mongodb_service.create_collection(database, collection)

        if result["status"] == "error":
            return f"Error: {result['message']}"

        logger.info("[tool:create_collection] Created %s.%s", database, collection)
        return f"Collection '{collection}' created in database '{database}'."
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error("[tool:create_collection] %s", e)
        return f"Error: {e}"


@mcp.tool()
async def create_index(
    database: str,
    collection: str,
    keys: str,
    unique: bool = False,
    name: str | None = None,
) -> str:
    """Create an index on a collection. keys: JSON array of [field, direction] pairs. Example: '[["name", 1], ["age", -1]]'"""
    logger.info("[tool:create_index] Called with db='%s', col='%s', unique=%s", database, collection, unique)
    try:
        parsed_keys = json.loads(keys)
    except json.JSONDecodeError as e:
        logger.warning("[tool:create_index] Invalid JSON keys: %s", e)
        return "Error: keys must be a valid JSON array of [field, direction] pairs."

    if not isinstance(parsed_keys, list):
        return "Error: keys must be a JSON array. Example: '[[\"name\", 1], [\"age\", -1]]'"

    try:
        result = await mongodb_service.create_index(database, collection, parsed_keys, unique=unique, name=name)

        if result["status"] == "not_found":
            return _format_not_found(result)
        if result["status"] == "error":
            return f"Error: {result['message']}"

        index_name = result["index_name"]
        logger.info("[tool:create_index] Created index '%s'", index_name)
        return f"Index '{index_name}' created on {database}.{collection}."
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error("[tool:create_index] %s", e)
        return f"Error: {e}"
