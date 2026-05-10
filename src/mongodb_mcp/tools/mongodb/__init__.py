"""MongoDB tools package — registers all MCP tools via sub-module imports."""

from . import metadata, create, read, update, delete

# Re-export tool objects so existing imports like
# `from mongodb_mcp.tools.mongodb import insert_one` continue to work.
from .metadata import (  
    list_databases,
    list_collections,
    collection_schema,
    collection_indexes,
    db_stats,
    explain_query,
    get_logs,
    collection_stats,
)
from .create import insert_one, insert_many, create_collection, create_index  
from .read import find, aggregate, count_documents, distinct  
from .update import update_one, update_many, rename_collection  
from .delete import delete_one, delete_many, drop_collection, drop_database, drop_index  
