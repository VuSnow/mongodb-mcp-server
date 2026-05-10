"""Read tools: find, aggregate, count, distinct."""
import json
import logging

from mongodb_mcp.app import mcp
from mongodb_mcp.services.mongodb import mongodb_service

from ._utils import _format_not_found

logger = logging.getLogger(__name__)


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
