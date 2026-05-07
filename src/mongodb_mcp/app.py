from fastmcp import FastMCP

mcp = FastMCP(
    name="MongoDB MCP Server",
    instructions=(
        "You are a MongoDB assistant. Use the available tools to help users "
        "interact with their MongoDB databases - querying data, managing collections, "
        "and inspecting database structure."
    )
)
