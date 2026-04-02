# Import depdendencies
from mcp.server.fastmcp import FastMCP

# Server created
mcp = FastMCP("Utility Tools", host="0.0.0.0", port=8080)

# Import all the tools
from tools import *

if __name__ == "__main__":
    #mcp.run(transport="stdio") # change the transport to "sse" to deploy as remote MCP server
    mcp.run(transport="sse")  # change the transport to "stdio" to run locally
