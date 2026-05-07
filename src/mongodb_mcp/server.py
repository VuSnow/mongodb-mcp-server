from fastmcp import FastMCP
from mongodb_mcp.configs import configs

mcp = FastMCP(
    name="MongoDB MCP Server",
    instructions=(
        "You are a MongoDB assistant. Use the available tools to help users "
        "interact with their MongoDB databases - querying data, managing collections, "
        "and inspecting database structure."
    )
)

# Register tools
import mongodb_mcp.tools.connection
import mongodb_mcp.tools.mongodb  


def main():
    """Entry point for running the server."""
    mcp.run()


if __name__ == "__main__":
    main()
