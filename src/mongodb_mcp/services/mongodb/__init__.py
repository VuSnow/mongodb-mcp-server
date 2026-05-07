from .metadata import MetadataService

class MongoDBService(MetadataService):
    """Full MongoDB service. Add more mixins (ReadService, CreateService, ...) in later phases."""
    pass

mongodb_service = MongoDBService()