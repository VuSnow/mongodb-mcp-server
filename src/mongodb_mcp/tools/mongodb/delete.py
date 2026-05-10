"""Delete tools: delete documents, drop collections, databases, and indexes."""
import json
import logging

from mongodb_mcp.app import mcp
from mongodb_mcp.services.mongodb import mongodb_service

from ._utils import _format_not_found

logger = logging.getLogger(__name__)


@mcp.tool()
async def delete_one(database: str, collection: str, filter: str) -> dict:
    """Delete a single document matching the filter. filter: JSON string of the match criteria."""
    logger.info(f"[tool:delete_one] Called with db='{database}', col='{collection}'")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:delete_one] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        result = await mongodb_service.delete_one(database, collection, parsed_filter)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        count = result["deleted_count"]
        logger.info(f"[tool:delete_one] deleted_count={count}")
        return {"result": f"Deleted {count} document(s) from {database}.{collection}."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:delete_one] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def delete_many(database: str, collection: str, filter: str) -> dict:
    """Delete all documents matching the filter. filter: JSON string of the match criteria. Use '{}' to delete all documents."""
    logger.info(f"[tool:delete_many] Called with db='{database}', col='{collection}'")
    try:
        parsed_filter = json.loads(filter)
    except json.JSONDecodeError as e:
        logger.warning(f"[tool:delete_many] Invalid JSON filter: {e}")
        return {"result": "Error: filter must be a valid JSON string."}

    try:
        result = await mongodb_service.delete_many(database, collection, parsed_filter)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        count = result["deleted_count"]
        logger.info(f"[tool:delete_many] deleted_count={count}")
        return {"result": f"Deleted {count} document(s) from {database}.{collection}."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:delete_many] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def drop_collection(database: str, collection: str) -> dict:
    """Drop a collection and all its documents and indexes. This operation is irreversible."""
    logger.info(f"[tool:drop_collection] Called with db='{database}', col='{collection}'")
    try:
        result = await mongodb_service.drop_collection(database, collection)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:drop_collection] Dropped {database}.{collection}")
        return {"result": f"Collection '{collection}' dropped from database '{database}'."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:drop_collection] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def drop_database(database: str) -> dict:
    """Drop an entire database and all its collections. This operation is irreversible."""
    logger.info(f"[tool:drop_database] Called with db='{database}'")
    try:
        result = await mongodb_service.drop_database(database)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:drop_database] Dropped database '{database}'")
        return {"result": f"Database '{database}' dropped successfully."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:drop_database] {e}")
        return {"result": f"Error: {e}"}


@mcp.tool()
async def drop_index(database: str, collection: str, index_name: str) -> dict:
    """Drop an index by name from a collection. Use collection_indexes to find index names."""
    logger.info(f"[tool:drop_index] Called with db='{database}', col='{collection}', index='{index_name}'")
    try:
        result = await mongodb_service.drop_index(database, collection, index_name)

        if result["status"] == "not_found":
            return {"result": _format_not_found(result)}
        if result["status"] == "error":
            return {"result": f"Error: {result['message']}"}

        logger.info(f"[tool:drop_index] Dropped index '{index_name}' on {database}.{collection}")
        return {"result": f"Index '{index_name}' dropped from {database}.{collection}."}
    except (ConnectionError, ValueError, PermissionError) as e:
        logger.error(f"[tool:drop_index] {e}")
        return {"result": f"Error: {e}"}
