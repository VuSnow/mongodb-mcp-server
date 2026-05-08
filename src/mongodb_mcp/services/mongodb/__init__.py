from .metadata import MetadataService
from .create import CreateService
from .read import ReadService
from .update import UpdateService
from .delete import DeleteService


class MongoDBService(MetadataService, CreateService, ReadService, UpdateService, DeleteService):
    """Full MongoDB service. Combines all operation mixins."""
    pass

mongodb_service = MongoDBService()