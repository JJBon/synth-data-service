"""
AgentCore Runtime Entrypoint for NeMo Data Designer MCP Server.

This wrapper runs the MCP server with streamable-http transport
as required by AWS Bedrock AgentCore Runtime.

Deploy with:
    pip install bedrock-agentcore-starter-toolkit
    agentcore configure -e agentcore_server.py --protocol MCP
    agentcore launch
"""

import os

import sys
import traceback

# Debug Print
print("DEBUG: Starting AgentCore Server Entrypoint...", flush=True)

# Set transport to streamable-http for AgentCore Runtime
os.environ["MCP_TRANSPORT"] = "streamable-http"

# Import and run the existing MCP server
try:
    print("DEBUG: Importing server_sdk...", flush=True)
    from server_sdk import mcp
    print("DEBUG: Import successful.", flush=True)
except Exception as e:
    print("CRITICAL: Failed to import server_sdk", flush=True)
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    # AgentCore expects the server at 0.0.0.0:8000/mcp
    print("DEBUG: Running MCP server...", flush=True)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)
