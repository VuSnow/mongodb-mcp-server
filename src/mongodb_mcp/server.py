from mongodb_mcp.app import mcp

import mongodb_mcp.tools.connection
import mongodb_mcp.tools.mongodb

def main():
    """Entry point for running the server."""
    mcp.run()

if __name__ == "__main__":
    main()
