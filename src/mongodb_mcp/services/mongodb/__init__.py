from .metadata import MetadataService
from .create import CreateService
from .read import ReadService
from .update import UpdateService


class MongoDBService(MetadataService, CreateService, ReadService, UpdateService):
    """Full MongoDB service. Combines all operation mixins."""
    pass

mongodb_service = MongoDBService()