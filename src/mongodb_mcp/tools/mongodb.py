import json
import logging

from mongodb_mcp.app import mcp
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


# ── Create Tools ─────────────────────────────────────────────────────────────


@mcp.tool()
async def insert_one(database: str, collection: str, document: str) -> dict:
    """Insert a single document into a collection. document: JSON string of the document to insert."""
    logger.info(f"[tool:insert_one] Called with db='{database}', col='{collection}'")
    try:
        parsed_doc = json.loads(document)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:insert_one] Invalid JSON document: {e}")
        return {"result": "Error: document must be a valid JSON string."}

    try:
        result = await mongodb_service.insert_one(database, collection, parsed_doc)

        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:insert_one] Inserted id={result['inserted_id']}")
        return {"result": f"Inserted 1 document into {database}.{collection}.\nInserted ID: {result['inserted_id']}"}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:insert_one] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def insert_many(database: str, collection: str, documents: str, ordered: bool = False) -> dict:
    """Insert multiple documents into a collection. documents: JSON array of documents."""
    logger.info(f"[tool:insert_many] Called with db='{database}', col='{collection}', ordered={ordered}")
    try:
        parsed_docs = json.loads(documents)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:insert_many] Invalid JSON: {e}")
        return {"result": "Error: documents must be a valid JSON array."}

    if not isinstance(parsed_docs, list):
        return {"result": "Error: documents must be a JSON array of objects."}

    try:
        result = await mongodb_service.insert_many(database, collection, parsed_docs, ordered=ordered)

        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        count = result["inserted_count"]
        logger.info(f"[tool:insert_many] Inserted {count} documents")
        return {"result": f"Inserted {count} documents into {database}.{collection}.\nInserted IDs: {json.dumps(result['inserted_ids'])}"}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:insert_many] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def create_collection(database: str, collection: str) -> dict:
    """Create a new collection in a database."""
    logger.info(f"[tool:create_collection] Called with db='{database}', col='{collection}'")
    try:
        result = await mongodb_service.create_collection(database, collection)

        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:create_collection] Created {database}.{collection}")
        return {"result": f"Collection '{collection}' created in database '{database}'."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:create_collection] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def create_index(
    database: str,
    collection: str,
    keys: str,
    unique: bool = False,
    name: str | None = None,
) -> dict:
    """Create an index on a collection. keys: JSON array of [field, direction] pairs. Example: '[["name", 1], ["age", -1]]'"""
    logger.info(f"[tool:create_index] Called with db='{database}', col='{collection}', unique={unique}")
    try:
        parsed_keys = json.loads(keys)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:create_index] Invalid JSON keys: {e}")
        return {"result": "Error: keys must be a valid JSON array of [field, direction] pairs."}

    if not isinstance(parsed_keys, list):
        return {"result": "Error: keys must be a JSON array. Example: '[[\"name\", 1], [\"age\", -1]]'"}

    try:
        result = await mongodb_service.create_index(database, collection, parsed_keys, unique=unique, name=name)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        index_name = result["index_name"]
        logger.info(f"[tool:create_index] Created index '{index_name}'")
        return {"result": f"Index '{index_name}' created on {database}.{collection}."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:create_index] {e}")
        return {"result": f"Error: {e}"}


# ── Read Tools ───────────────────────────────────────────────────────────────


@mcp.tool()
async def find(
    database: str,
    collection: str,
    filter: str = "{}",
    projection: str | None = None,
    sort: str | None = None,
    skip: int = 0,
    limit: int = 10,
) -> dict:
    """Query documents from a collection. filter/projection/sort: JSON strings. sort: array of [field, direction] pairs."""
    logger.info(f"[tool:find] Called with db='{database}', col='{collection}', skip={skip}, limit={limit}")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:find] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    parsed_projection = None
    if projection:
        try:
            parsed_projection = json.loads(projection)
        except json.JSONDecodeError as e:
            logger.warning(f"[tool:find] Invalid JSON projection: {e}")
            return {"result": "Error: projection must be a valid JSON string."}

    parsed_sort = None
    if sort:
        try:
            parsed_sort = json.loads(sort)
        except json.JSONDecodeError as e:
            logger.warning(f"[tool:find] Invalid JSON sort: {e}")
            return {"result": "Error: sort must be a valid JSON array of [field, direction] pairs."}

    try:
        result = await mongodb_service.find(
            database, collection,
            filter=parsed_filter, projection=parsed_projection,
            sort=parsed_sort, skip=skip, limit=limit,
        )

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        documents = result["documents"]
        count = result["count"]
        if not documents:
            logger.info(f"[tool:find] {database}.{collection} returned 0 results")
            return {"result": f"Query returned 0 documents from {database}.{collection}."}
        logger.info(f"[tool:find] Returning {count} documents")
        return {"result": f"Found {count} documents in {database}.{collection}:\n{json.dumps(documents, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:find] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def aggregate(
    database: str,
    collection: str,
    pipeline: str,
    limit: int = 1000,
) -> dict:
    """Run an aggregation pipeline. pipeline: JSON array of stage objects."""
    logger.info(f"[tool:aggregate] Called with db='{database}', col='{collection}', limit={limit}")
    try:
        parsed_pipeline = json.loads(pipeline)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:aggregate] Invalid JSON pipeline: {e}")
        return {"result": "Error: pipeline must be a valid JSON array of stage objects."}

    if not isinstance(parsed_pipeline, list):
        return {"result": "Error: pipeline must be a JSON array. Example: '[{\"$match\": {\"status\": \"active\"}}]'"}

    try:
        result = await mongodb_service.aggregate(database, collection, parsed_pipeline, limit=limit)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        results = result["results"]
        count = result["count"]
        logger.info(f"[tool:aggregate] Returning {count} results")
        return {"result": f"Aggregation returned {count} results from {database}.{collection}:\n{json.dumps(results, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:aggregate] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def count_documents(
    database: str,
    collection: str,
    filter: str = "{}",
) -> dict:
    """Count documents matching a filter in a collection."""
    logger.info(f"[tool:count_documents] Called with db='{database}', col='{collection}'")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:count_documents] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        result = await mongodb_service.count_documents(database, collection, filter=parsed_filter)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}

        count = result["count"]
        logger.info(f"[tool:count_documents] {database}.{collection} has {count} documents")
        return {"result": f"{database}.{collection} has {count} documents matching the filter."}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:count_documents] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def distinct(
    database: str,
    collection: str,
    field: str,
    filter: str = "{}",
) -> dict:
    """Get distinct values of a field in a collection. Useful for discovering enum-like values (e.g. status, type, category)."""
    logger.info(f"[tool:distinct] Called with db='{database}', col='{collection}', field='{field}'")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:distinct] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        result = await mongodb_service.distinct(database, collection, field, filter=parsed_filter)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        values = result["values"]
        count = result["count"]
        logger.info(f"[tool:distinct] {database}.{collection}.{field} has {count} distinct values")
        return {"result": f"Field '{field}' in {database}.{collection} has {count} distinct values:\n{json.dumps(values, indent=2, default=str)}"}
    except (ConnectionError, ValueError) as e:
        logger.error(f"[tool:distinct] {e}")
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

        # Format key metrics for LLM readability
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


# ── Update Tools ─────────────────────────────────────────────────────────────


@mcp.tool()
async def update_one(
    database: str,
    collection: str,
    filter: str,
    update: str,
    upsert: bool = False,
) -> dict:
    """Update a single document matching the filter. filter/update: JSON strings. update must use operators like $set, $inc."""
    logger.info(f"[tool:update_one] Called with db='{database}', col='{collection}', upsert={upsert}")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:update_one] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        parsed_update = json.loads(update)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:update_one] Invalid JSON update: {e}")
        return {"result": "Error: update must be a valid JSON string."}

    try:
        result = await mongodb_service.update_one(database, collection, parsed_filter, parsed_update, upsert=upsert)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        matched = result["matched_count"]
        modified = result["modified_count"]
        upserted_id = result.get("upserted_id")
        msg = f"Matched {matched}, modified {modified} document(s) in {database}.{collection}."
        if upserted_id:
            msg += f"\nUpserted ID: {upserted_id}"
        logger.info(f"[tool:update_one] {msg}")
        return {"result": msg}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:update_one] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def update_many(
    database: str,
    collection: str,
    filter: str,
    update: str,
    upsert: bool = False,
) -> dict:
    """Update all documents matching the filter. filter/update: JSON strings. update must use operators like $set, $inc."""
    logger.info(f"[tool:update_many] Called with db='{database}', col='{collection}', upsert={upsert}")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:update_many] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        parsed_update = json.loads(update)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:update_many] Invalid JSON update: {e}")
        return {"result": "Error: update must be a valid JSON string."}

    try:
        result = await mongodb_service.update_many(database, collection, parsed_filter, parsed_update, upsert=upsert)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        matched = result["matched_count"]
        modified = result["modified_count"]
        upserted_id = result.get("upserted_id")
        msg = f"Matched {matched}, modified {modified} document(s) in {database}.{collection}."
        if upserted_id:
            msg += f"\nUpserted ID: {upserted_id}"
        logger.info(f"[tool:update_many] {msg}")
        return {"result": msg}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:update_many] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def rename_collection(
    database: str,
    collection: str,
    new_name: str,
    drop_target: bool = False,
) -> dict:
    """Rename a collection within a database. Set drop_target=true to overwrite an existing target collection."""
    logger.info(f"[tool:rename_collection] Called with db='{database}', col='{collection}' -> '{new_name}'")
    try:
        result = await mongodb_service.rename_collection(database, collection, new_name, drop_target=drop_target)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:rename_collection] Renamed {database}.{collection} -> {database}.{new_name}")
        return {"result": f"Collection renamed from '{collection}' to '{new_name}' in database '{database}'."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:rename_collection] {e}")
        return {"result": f"Error: {e}"}
