"""Agent runner for connecting Streamlit to LangGraph agent."""
import asyncio
import os
from typing import AsyncGenerator, Optional
from mcp import ClientSession
from mcp.client.sse import sse_client


MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL", "http://localhost:8002/sse")


class AgentRunner:
    """Run the synth data agent with streaming support."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.tools: dict = {}
    
    async def connect(self):
        """Connect to MCP server."""
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                self.session = session
                await session.initialize()
                
                # Get available tools
                tools_result = await session.list_tools()
                self.tools = {t.name: t for t in tools_result.tools}
    
    async def call_tool(self, name: str, args: dict) -> dict:
        """Call a single MCP tool."""
        if not self.session:
            return {"error": "Not connected to MCP server"}
        
        result = await self.session.call_tool(name, args)
        return result.content[0].text if result.content else {}
    
    async def generate_data(self, prompt: str) -> AsyncGenerator[dict, None]:
        """
        Generate data based on user prompt.
        Yields steps for real-time UI updates.
        """
        async with sse_client(MCP_SERVER_URL) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Step 1: Initialize config
                yield {"type": "status", "message": "Initializing configuration..."}
                result = await session.call_tool("init_config", {})
                yield {"type": "tool_result", "tool": "init_config", "result": result}
                
                # The actual generation logic would be handled by the LLM
                # For now, return a placeholder
                yield {"type": "status", "message": "Ready for generation. Use chat to describe your data."}


def run_sync(coro):
    """Run async coroutine synchronously (for Streamlit)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
