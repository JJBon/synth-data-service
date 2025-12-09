
import os
import sys
import json
import asyncio
from typing import Dict, Any, Optional
import logging

from bedrock_agentcore import BedrockAgentCoreApp
from bedrock_agentcore.runtime.context import RequestContext

# Add root directory to path to import local modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import from refactored agent.py
from langgraph.agent import create_graph, DesignState
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = BedrockAgentCoreApp()

async def run_bedrock_invocation(prompt: str, session_id: str):
    """
    Async helper to set up the MCP connection and run the graph for a single turn.
    """
    # 1. Connect to MCP (Same URL as local, assuming sidecar/network reachability)
    # In AWS Bedrock environment, this might be a localhost URL if running in same pod
    # or a service URL. Defaulting to localhost for now.
    url = os.environ.get("MCP_SERVER_URL", "http://localhost:8002/sse")
    logger.info(f"Connecting to MCP at {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # 2. Discover Tools
            tools_list = await session.list_tools()
            logger.info(f"Discovered {len(tools_list.tools)} tools.")
            
            # 3. Setup LLM (Using LiteLLM Proxy or AWS Bedrock direct)
            formatted_tools = []
            for t in tools_list.tools:
                formatted_tools.append({
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.inputSchema
                    }
                })
            
            model_name = os.environ.get("LLM_MODEL", "bedrock-claude-haiku")
            llm_url = os.environ.get("LLM_BASE_URL", "http://localhost:4000/v1")
            llm_key = os.environ.get("LITELLM_KEY", "sk-placeholder")
            
            llm = ChatOpenAI(model=model_name, temperature=0, base_url=llm_url, api_key=llm_key)
            llm_with_tools = llm.bind_tools(formatted_tools)

            # 4. Create Graph
            graph = await create_graph(session, llm_with_tools)
            
            # 5. Invoke Graph with User Input
            # Note: Bedrock Agent is stateless between invocations unless memory is managed.
            # We treat each invocation as a new 'turn' but we need the history.
            # For simplicity in this v1 adapter, we send just the current prompt.
            # Real implementation needs state persistence (Check article for memory implementation).
            
            initial_state = {"messages": [HumanMessage(content=prompt)], "mpc_tool_calls": []}
            config = {"configurable": {"session": session, "llm_with_tools": llm_with_tools}, "recursion_limit": 50}
            
            # Invoke the graph
            # We likely need to adjust the graph to NOT be an infinite loop of input->response
            # but rather run until it hits "human_input" again.
            
            result = await graph.ainvoke(initial_state, config=config)
            
            # Extract the last message content
            last_message = result["messages"][-1]
            return last_message.content

@app.entrypoint
def invoke(payload: Dict[str, Any], context: Optional[RequestContext] = None) -> Dict[str, Any]:
    """
    Main entrypoint for Bedrock AgentCore.
    """
    logger.info("LangGraph AgentCore invocation started")
    
    prompt = payload.get("prompt", "")
    session_id = context.session_id if context else payload.get("session_id", "default-session")
    
    if not prompt:
        return {"result": "Error: No prompt provided."}

    try:
        # Run the async logic synchronously
        result_text = asyncio.run(run_bedrock_invocation(prompt, session_id))
        return {"result": result_text}
        
    except Exception as e:
        logger.error(f"Error invoking agent: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    # Local testing support stub
    pass
