
from fastmcp import FastMCP
import os
import sys

print("DEBUG: Minimal Server Starting...", flush=True)

# Initialize FastMCP
mcp = FastMCP("minimal-server", streamable_http_path="/")

@mcp.tool()
def probe() -> str:
    return "Minimal Server is Alive"

if __name__ == "__main__":
    print("DEBUG: Starting uvicorn...", flush=True)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8080)
