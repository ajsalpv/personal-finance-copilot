from mcp.server.fastmcp import FastMCP
from app.ai.tools import all_tools
import logging

logger = logging.getLogger(__name__)

# Create the MCP server
mcp = FastMCP("Callista")

# Register all existing tools with the MCP server
for tool in all_tools:
    @mcp.tool(name=tool.name)
    async def mcp_tool_wrapper(*args, **kwargs):
        """MCP Wrapper for Callista tools."""
        return await tool.func(*args, **kwargs)

@mcp.resource("user://profile")
def get_user_profile() -> str:
    """Standardized resource for user context via ANP."""
    return "Callista User: Premium Personal Finance Context"

def start_mcp_server():
    """Starts the MCP server (SSE mode)."""
    logger.info("Starting Callista MCP Server...")
    # In a production setup, this would run as a separate process or SSE endpoint.
    # For now, we provide the definition.
    pass
