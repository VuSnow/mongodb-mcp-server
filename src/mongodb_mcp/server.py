from mongodb_mcp.app import mcp

# Register tools (side-effect imports)
import mongodb_mcp.tools.connection  # noqa: F401
import mongodb_mcp.tools.mongodb  # noqa: F401

def main():
    """Entry point for running the server."""
    mcp.run()

if __name__ == "__main__":
    main()
