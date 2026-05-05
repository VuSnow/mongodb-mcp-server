from .create import CreateClient
from .read import ReadClient
from .update import UpdateClient
from .metadata import MetadataClient
from .delete import DeleteClient

__all__ = ["MongoDBClient"]

class MongoDBClient(MetadataClient, ReadClient, CreateClient, UpdateClient, DeleteClient):
    """Full MongoDB client — combines all operation types via mixin inheritance."""
    pass
