
from fastmcp import FastMCP
import os

# Initialize FastMCP with a simple name
mcp = FastMCP("mock-agent-core-server")

@mcp.tool()
def probe_connectivity() -> dict:
    """
    A simple probe tool to verify connectivity to the MCP server.
    Returns network and environment details.
    """
    return {
        "status": "connected",
        "message": "Hello from the Mock MCP Server!",
        "env": {
            "mcp_transport": os.environ.get("MCP_TRANSPORT"),
            "host": os.environ.get("HOSTNAME", "unknown")
        }
    }

@mcp.tool()
def echo(message: str) -> str:
    """
    Echoes back the message to verify input/output parameters.
    """
    return f"Echo: {message}"

@mcp.tool()
def ping_service(url: str, timeout: float = 5.0) -> dict:
    """
    Ping an internal HTTP service to verify connectivity.
    Useful for checking if Agent Core can reach EKS services (e.g. NeMo, LiteLLM).
    
    Args:
        url: The full URL to check (e.g. http://nemo-data-designer:8000/health)
        timeout: Timeout in seconds
    """
    import urllib.request
    import urllib.error
    import time
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return {
                "status": "success",
                "code": response.getcode(),
                "latency_ms": (time.time() - start_time) * 1000,
                "url": url
            }
    except urllib.error.URLError as e:
        return {
            "status": "error",
            "error": str(e),
            "url": url,
            "latency_ms": (time.time() - start_time) * 1000
        }
    except Exception as e:
        return {
            "status": "error",
            "error": f"Unexpected error: {str(e)}",
            "url": url
        }

if __name__ == "__main__":
    # AgentCore expects the server at 0.0.0.0:8000/mcp (or just port 8000 depending on path routing)
    # We use streamable-http as required
    print("Starting Mock MCP Server on 0.0.0.0:8000...")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
