from mongodb_mcp.server import mcp
from mongodb_mcp.services.connection_manager import connection_manager
import logging

logger = logging.getLogger(__name__)

@mcp.tool()
async def connect(connection_string: str | None = None):
    """Connect to a MongoDB instance. Uses configured connection string if not provided."""
    try:
        await connection_manager.connect(connection_string)
        logger.info("Connect successfully!")
        return "Connected to MongoDB successfully."
    except ConnectionError as e:
        logger.error(f"Connect failed: {e}", exc_info=True)
        return f"Failed to connect: {e}"
    
@mcp.tool()
async def disconnect() -> str:
    """Disconnect from the current MongoDB instance."""
    await connection_manager.disconnect()
    logger.info("Disconnected.")
    return "Disconnected from MongoDB."
