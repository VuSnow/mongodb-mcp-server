from .metadata import MetadataService
from .create import CreateService
from .read import ReadService


class MongoDBService(MetadataService, CreateService, ReadService):
    """Full MongoDB service. Combines all operation mixins."""
    pass

mongodb_service = MongoDBService()