# Deploying MCP Server to Amazon Bedrock AgentCore

To deploy this MCP server to AWS Bedrock AgentCore, follow these steps:

## Prerequisites
1.  Install the `bedrock-agentcore-starter-toolkit`:
    ```bash
    pip install bedrock-agentcore-starter-toolkit
    ```
2.  Ensure you have AWS credentials configured.

## Deployment Steps
1.  Navigate to this directory:
    ```bash
    cd mcp_server_py
    ```
2.  Configure the deployment:
    ```bash
    agentcore configure -e server_sdk.py --protocol MCP
    ```
    - **Note**: You may need to create a `requirements.txt` if one doesn't exist (see below).
3.  Launch the agent:
    ```bash
    agentcore launch
    ```

## Environment Variables
The code handles `MCP_TRANSPORT=streamable-http` and `MCP_STATELESS=true` automatically when running in the AgentCore runtime.

## Requirements
Ensure `requirements.txt` contains:
```
mcp
fastmcp
httpx
# nemo_microservices (if available in your environment/container)
```
