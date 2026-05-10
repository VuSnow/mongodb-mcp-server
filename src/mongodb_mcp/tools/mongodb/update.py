"""Update tools: update documents, rename collections."""
import json
import logging

from mongodb_mcp.app import mcp
from mongodb_mcp.services.mongodb import mongodb_service

from ._utils import _format_not_found

logger = logging.getLogger(__name__)


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
