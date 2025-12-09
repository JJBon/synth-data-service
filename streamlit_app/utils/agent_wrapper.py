"""
LangGraph-based agent for Streamlit with user interaction support.
Uses a stateful agent pattern for multi-turn conversations.
"""
import sys
import os
import json
import asyncio
from typing import TypedDict, Annotated, List, Dict, Any, Optional, Callable
from pathlib import Path
import operator

# Add langgraph to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "langgraph"))

from mcp import ClientSession
from mcp.client.sse import sse_client
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage


MCP_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server-sdk:8002/sse")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://host.docker.internal:4000/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "bedrock-claude-haiku")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-master-123")


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
    job_id: Optional[str]
    final_result: Optional[Dict]
    needs_user_input: bool
    user_prompt: str


SYSTEM_PROMPT = """
You are a Data Designer AI that generates synthetic datasets.

WORKFLOW PHASES:
1. PLANNING: When user describes what they want, propose a schema with columns
2. WAIT FOR CONFIRMATION: Ask user to confirm before generating
3. GENERATION: If user confirms, execute the full workflow

When user gives initial request:
- Propose a schema with columns (don't generate yet)
- Ask: "Does this schema look good? Reply 'yes' to generate or describe changes."

When user confirms (says yes/proceed/generate/submit):
- Execute: init_config → add columns → create_job → get_job_status → finalize_job
- MUST complete all steps including finalize_job

TOOLS:
- init_config: Start fresh configuration
- add_uuid_column, add_person_column, add_datetime_column, add_float_column, add_category_column
- create_job: Submit job (returns job_id)
- get_job_status: Check job status (poll until completed)
- finalize_job: REQUIRED - Save results and get file paths

CRITICAL: After finalize_job, report the file paths to user.
"""


class StreamlitAgent:
    """
    Stateful agent that maintains conversation and allows user interaction.
    """
    
    def __init__(self, status_callback: Optional[Callable[[str], None]] = None):
        self.status_callback = status_callback
        self.session = None
        self.llm_with_tools = None
        self.messages: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
        self.job_id = None
        self.connected = False
    
    def log(self, msg: str):
        if self.status_callback:
            self.status_callback(msg)
    
    async def connect(self):
        """Connect to MCP and initialize LLM."""
        if self.connected:
            return
        
        self.log("🔌 Connecting to MCP server...")
        
        # We need to keep the context managers open
        self._sse_context = sse_client(MCP_URL)
        read, write = await self._sse_context.__aenter__()
        
        self._session_context = ClientSession(read, write)
        self.session = await self._session_context.__aenter__()
        await self.session.initialize()
        
        self.log("✅ Connected to MCP server")
        
        # Get tools
        tools_result = await self.session.list_tools()
        tool_defs = []
        for t in tools_result.tools:
            tool_defs.append({
                "name": t.name,
                "description": t.description,
                "parameters": t.inputSchema
            })
        
        self.log(f"📋 Found {len(tool_defs)} tools")
        
        # Initialize LLM
        llm = ChatOpenAI(
            base_url=LLM_BASE_URL,
            api_key=LLM_API_KEY,
            model=LLM_MODEL,
            temperature=0.7
        )
        self.llm_with_tools = llm.bind_tools(tool_defs)
        self.connected = True
    
    async def disconnect(self):
        """Clean up connections."""
        if hasattr(self, '_session_context'):
            await self._session_context.__aexit__(None, None, None)
        if hasattr(self, '_sse_context'):
            await self._sse_context.__aexit__(None, None, None)
        self.connected = False
    
    async def process_message(self, user_message: str) -> str:
        """
        Process a user message and return the agent's response.
        May include tool calls and polling.
        """
        if not self.connected:
            await self.connect()
        
        # Add user message
        self.messages.append(HumanMessage(content=user_message))
        
        self.log("🤖 Thinking...")
        
        # Agent loop
        max_iterations = 25
        for i in range(max_iterations):
            # Call LLM
            response = await self.llm_with_tools.ainvoke(self.messages)
            self.messages.append(response)
            
            # No tool calls - LLM wants to respond to user
            if not response.tool_calls:
                self.log("💬 Agent responding...")
                return response.content
            
            # Execute tool calls - collect all results first
            tool_messages = []
            for tool_call in response.tool_calls:
                tool_name = tool_call["name"]
                args = tool_call["args"]
                
                self.log(f"🔧 {tool_name}: {json.dumps(args)[:60]}...")
                
                try:
                    result = await self.session.call_tool(tool_name, arguments=args)
                    
                    # Extract result text
                    result_text = ""
                    if result.content:
                        for c in result.content:
                            if hasattr(c, "text"):
                                result_text += c.text
                    
                    # Parse and track
                    try:
                        result_obj = json.loads(result_text)
                    except:
                        result_obj = {"text": result_text}
                    
                    if tool_name == "create_job":
                        self.job_id = result_obj.get("job_id")
                        self.log(f"📤 Job submitted: {self.job_id}")
                    
                    if tool_name == "get_job_status":
                        status = result_obj.get("status", "unknown")
                        self.log(f"⏳ Status: {status}")
                    
                    if tool_name == "finalize_job":
                        self.log("✅ Job finalized!")
                        files = result_obj.get("local_files", {})
                        if files.get("csv"):
                            self.log(f"📁 CSV: {files['csv']}")
                    
                    self.log(f"✓ {tool_name} done")
                    
                    tool_messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=result_text
                    ))
                    
                except Exception as e:
                    self.log(f"❌ {tool_name} error: {e}")
                    tool_messages.append(ToolMessage(
                        tool_call_id=tool_call["id"],
                        content=f"Error: {e}"
                    ))
            
            # Append all tool messages at once after processing all tool calls
            self.messages.extend(tool_messages)
        
        return "Max iterations reached. Please try again."


# Global agent instance for Streamlit session
_agent_instance: Optional[StreamlitAgent] = None


def get_agent(status_callback: Callable[[str], None] = None) -> StreamlitAgent:
    """Get or create agent instance."""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = StreamlitAgent(status_callback)
    else:
        _agent_instance.status_callback = status_callback
    return _agent_instance


def reset_agent():
    """Reset the agent for a new conversation."""
    global _agent_instance
    if _agent_instance:
        asyncio.run(_agent_instance.disconnect())
    _agent_instance = None


async def chat_with_agent(user_message: str, status_callback: Callable[[str], None] = None) -> str:
    """Send a message to the agent and get response."""
    agent = get_agent(status_callback)
    return await agent.process_message(user_message)


def chat_sync(user_message: str, status_callback: Callable[[str], None] = None) -> str:
    """Synchronous wrapper for chat_with_agent."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(chat_with_agent(user_message, status_callback))
    finally:
        loop.close()
