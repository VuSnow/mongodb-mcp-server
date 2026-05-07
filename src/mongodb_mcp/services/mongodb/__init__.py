from .metadata import MetadataService
from .create import CreateService


class MongoDBService(MetadataService, CreateService):
    """Full MongoDB service. Combines all operation mixins."""
    pass

mongodb_service = MongoDBService()