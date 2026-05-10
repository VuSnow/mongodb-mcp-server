"""Create tools: insert documents, create collections and indexes."""
import json
import logging

from mongodb_mcp.app import mcp
from mongodb_mcp.services.mongodb import mongodb_service

from ._utils import _format_not_found

logger = logging.getLogger(__name__)


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
