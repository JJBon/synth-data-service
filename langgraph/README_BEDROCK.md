# Deploying LangGraph Agent to Amazon Bedrock AgentCore

This directory contains the adapter code to run your LangGraph agent on AWS Bedrock.

## Files
- `bedrock_agent.py`: The entrypoint file that wraps your LangGraph agent.
- `agent.py`: The core agent logic (refactored to expose `create_graph`).

## Prerequisites
1.  **MCP Server**: You must have your MCP server (`mcp_server_py`) deployed and accessible (e.g., in a sidecar or reachable URL).
2.  **LiteLLM**: You must have a LiteLLM proxy instance reachable (or update the code to use Bedrock directly).

## Deployment
1.  Configure the agent:
    ```bash
    agentcore configure -e langgraph/bedrock_agent.py --protocol MCP
    ```
2.  Set Environment Variables:
    - `MCP_SERVER_URL`: URL to your MCP server (e.g., `http://localhost:8002/sse`)
    - `LLM_BASE_URL`: URL to your LLM proxy
    - `LITELLM_KEY`: Your API key

3.  Launch:
    ```bash
    agentcore launch
    ```

## Local Testing
You can test locally if you have the MCP server running on port 8002:
```bash
agentcore launch --local
agentcore invoke --local '{"prompt": "Generate a dataset for users"}'
```
