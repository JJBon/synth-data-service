"""
FastAPI SSE server for streaming LangGraph agent state to Streamlit.
Implements the three-layer architecture: LangGraph → FastAPI (SSE) → Streamlit
WITH Human-in-the-Loop confirmation before job creation.
"""
import os
import sys
import json
import asyncio
import uuid
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

# Add paths
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage, BaseMessage
from langchain_openai import ChatOpenAI
from mcp import ClientSession
from mcp.client.sse import sse_client
import operator
from typing import TypedDict, Annotated, List

# Environment variables
MCP_URL = os.environ.get("MCP_SERVER_URL", "http://mcp-server-sdk:8002/sse")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "http://host.docker.internal:4000/v1")
LLM_MODEL = os.environ.get("LLM_MODEL", "bedrock-claude-haiku")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "sk-1234")


# --- Session Storage for Multi-turn Conversations ---
sessions: Dict[str, Dict[str, Any]] = {}


# --- State Definition ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    tool_calls: Annotated[List[Dict[str, Any]], operator.add]
    job_id: Optional[str]
    job_status: str
    poll_count: int
    phase: str  # "planning", "awaiting_confirmation", "generating"


# --- SSE Formatting ---
def sse_format(payload: dict) -> str:
    """Format payload as Server-Sent Event."""
    return f"data: {json.dumps(payload)}\n\n"


# System prompt with HUMAN-IN-THE-LOOP requirement
SYSTEM_PROMPT = """You are a Data Designer AI that generates synthetic datasets via MCP tools.

WORKFLOW PHASES:

## PHASE 1: PLANNING (Current phase for new requests)
1. Call init_config to start fresh
2. Add columns based on user's request using: add_uuid_column, add_person_column, add_datetime_column, add_float_column, add_category_column
   - IMPORTANT: Use 'snake_case' for column names (e.g., 'short_description') to avoid Jinja2 template errors.
3. STOP and present the proposed schema to the user
4. Ask: "Does this schema look good? Reply 'yes' to generate, or describe changes."

## PHASE 2: GENERATION (Only after user confirms)
After user says "yes", "confirm", "proceed", "generate", or similar:
1. create_job - Submit the job
2. get_job_status - Keep polling until status='completed' (this may take 30-60 seconds)
3. finalize_job - Save results and get file paths
4. ONLY THEN respond to user with success message and download info

CRITICAL RULES:
- ALWAYS ask for confirmation BEFORE calling create_job
- If the user hasn't confirmed yet, DO NOT call create_job
- When asking for confirmation, list the columns you've defined
- After user confirms, complete ALL steps through finalize_job
- DO NOT respond to the user saying "I'll let you know" or "I'll poll the status"
- You MUST wait for the job to complete and call finalize_job BEFORE responding
- The entire workflow from create_job to finalize_job happens in ONE continuous stream
"""


# --- Graph Nodes ---
async def reasoner_node(state: AgentState, config):
    """LLM reasoning node with phase awareness."""
    llm_with_tools = config["configurable"]["llm_with_tools"]
    phase = state.get("phase", "planning")
    
    system_msg = SystemMessage(content=SYSTEM_PROMPT + f"\n\nCURRENT PHASE: {phase}")
    
    messages = state["messages"]
    if not any(isinstance(m, SystemMessage) for m in messages):
        all_messages = [system_msg] + messages
    else:
        # Update system message
        all_messages = [system_msg] + [m for m in messages if not isinstance(m, SystemMessage)]
    
    response = await llm_with_tools.ainvoke(all_messages)
    
    # Detect if LLM is asking for confirmation (no tool calls, has question marks)
    new_phase = phase
    if not response.tool_calls and response.content:
        content_lower = response.content.lower()
        if any(q in content_lower for q in ["does this", "look good", "confirm", "proceed?", "changes?"]):
            new_phase = "awaiting_confirmation"
        elif phase == "awaiting_confirmation" and any(w in content_lower for w in ["generating", "creating job", "submitting"]):
            new_phase = "generating"
    
    return {"messages": [response], "phase": new_phase}


async def tool_executor_node(state: AgentState, config):
    """Execute MCP tools with exponential backoff for polling."""
    session = config["configurable"]["session"]
    
    last_message = state["messages"][-1]
    if not last_message.tool_calls:
        return {"messages": [], "tool_calls": [], "poll_count": state.get("poll_count", 0)}
    
    tool_results = []
    tool_call_records = []
    poll_count = state.get("poll_count", 0)
    
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        
        # Exponential backoff for get_job_status
        if tool_name == "get_job_status":
            poll_count += 1
            delay = min(5 * poll_count, 30)
            await asyncio.sleep(delay)
        
        try:
            result = await session.call_tool(tool_name, arguments=args)
            
            # Extract text content
            output_str = ""
            if result.content:
                for c in result.content:
                    if hasattr(c, "text"):
                        output_str += c.text
            
            # Parse result
            try:
                result_obj = json.loads(output_str)
            except:
                result_obj = {"text": output_str}
            
            tool_results.append(ToolMessage(tool_call_id=tool_call["id"], content=output_str))
            tool_call_records.append({"name": tool_name, "result": result_obj, "args": args})
            
        except Exception as e:
            tool_results.append(ToolMessage(tool_call_id=tool_call["id"], content=f"Error: {e}"))
    
    # Update job_id and phase if create_job was called
    job_id = state.get("job_id")
    phase = state.get("phase", "planning")
    for record in tool_call_records:
        if record["name"] == "create_job" and isinstance(record["result"], dict):
            job_id = record["result"].get("job_id", job_id)
            phase = "generating"
    
    return {"messages": tool_results, "tool_calls": tool_call_records, "job_id": job_id, "poll_count": poll_count, "phase": phase}


async def job_poller_node(state: AgentState, config):
    """
    Automatically polls job status until completion, then calls finalize_job.
    This removes reliance on the LLM to keep calling get_job_status.
    """
    session = config["configurable"]["session"]
    job_id = state.get("job_id")
    
    if not job_id:
        return {"messages": [AIMessage(content="No job_id found to poll")]}
    
    # Poll for up to 120 seconds
    for poll_attempt in range(120):
        await asyncio.sleep(1)
        
        try:
            # Call get_job_status
            result = await session.call_tool("get_job_status", arguments={"job_id": job_id})
            
            output_str = ""
            if result.content:
                for c in result.content:
                    if hasattr(c, "text"):
                        output_str += c.text
            
            try:
                status_obj = json.loads(output_str)
                current_status = status_obj.get("status", "").lower()
                
                if current_status in ["completed", "success"]:
                    # Job completed! Now call import_results
                    session_id = config["configurable"].get("thread_id")
                    finalize_result = await session.call_tool("import_results", arguments={"job_id": job_id, "session_id": session_id})
                    
                    finalize_str = ""
                    if finalize_result.content:
                        for c in finalize_result.content:
                            if hasattr(c, "text"):
                                finalize_str += c.text
                    
                    return {
                        "messages": [AIMessage(content=f"✅ Job {job_id} completed! {finalize_str}")],
                        "job_status": "completed",
                        "phase": "complete"
                    }
                
                elif current_status in ["failed", "error"]:
                    error_details = status_obj.get("error_details", "Unknown error")
                    return {
                        "messages": [AIMessage(content=f"❌ Job {job_id} failed: {error_details}")],
                        "job_status": "failed"
                    }
                
                # Still running, continue polling
                if poll_attempt % 10 == 0:  # Log every 10 seconds
                    print(f"Polling job {job_id}: status={current_status}, attempt={poll_attempt}")
                    
            except json.JSONDecodeError:
                continue
                
        except Exception as e:
            print(f"Error polling job: {e}")
            continue
    
    # Timeout after 120 seconds
    return {
        "messages": [AIMessage(content=f"⏱️ Job {job_id} polling timed out after 120 seconds")],
        "job_status": "timeout"
    }


def should_continue(state: AgentState):
    """Route based on last message and phase."""
    last_message = state["messages"][-1]
    phase = state.get("phase", "planning")
    job_id = state.get("job_id")
    
    # If we just created a job, go to poller
    if job_id and phase == "generating":
        return "job_poller"
    
    # If awaiting confirmation and LLM responded without tools, stop for user input
    if phase == "awaiting_confirmation" and not (hasattr(last_message, "tool_calls") and last_message.tool_calls):
        return "end"
    
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_executor"
    return "end"


def create_agent_graph():
    """Create and return the compiled agent graph."""
    workflow = StateGraph(AgentState)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("job_poller", job_poller_node)
    
    workflow.add_edge(START, "reasoner")
    workflow.add_conditional_edges("reasoner", should_continue, {
        "tool_executor": "tool_executor",
        "job_poller": "job_poller",
        "end": END
    })
    workflow.add_edge("tool_executor", "reasoner")
    workflow.add_edge("job_poller", END)  # Poller goes directly to end when done
    
    return workflow.compile()


# --- FastAPI App ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup and teardown for FastAPI."""
    print("LangGraph FastAPI server starting (with human-in-the-loop)...")
    yield
    print("Shutting down...")


app = FastAPI(title="LangGraph SSE Server", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/generate")
async def generate_content(request: Request):
    """
    Stream agent execution via SSE with multi-turn support.
    Expects JSON body: {"message": "user request", "session_id": "optional"}
    """
    data = await request.json()
    user_message = data.get("message", "")
    session_id = data.get("session_id", str(uuid.uuid4()))
    
    async def stream_generator():
        yield sse_format({"type": "session", "session_id": session_id})
        yield sse_format({"type": "status", "message": "Connecting to MCP server..."})
        
        try:
            async with sse_client(MCP_URL) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield sse_format({"type": "status", "message": "Connected to MCP"})
                    
                    # Get tools
                    tools_result = await session.list_tools()
                    tool_defs = []
                    for t in tools_result.tools:
                        tool_defs.append({
                            "name": t.name,
                            "description": t.description,
                            "parameters": t.inputSchema
                        })
                    yield sse_format({"type": "status", "message": f"Found {len(tool_defs)} tools"})
                    
                    # Initialize LLM
                    llm = ChatOpenAI(
                        base_url=LLM_BASE_URL,
                        api_key=LLM_API_KEY,
                        model=LLM_MODEL,
                        temperature=0.7
                    )
                    llm_with_tools = llm.bind_tools(tool_defs)
                    
                    # Create graph
                    graph = create_agent_graph()
                    
                    # Get or create session state
                    if session_id in sessions:
                        # Continue existing session
                        prev_state = sessions[session_id]
                        initial_state = {
                            "messages": prev_state["messages"] + [HumanMessage(content=user_message)],
                            "tool_calls": prev_state.get("tool_calls", []),
                            "job_id": prev_state.get("job_id"),
                            "job_status": prev_state.get("job_status", "pending"),
                            "poll_count": prev_state.get("poll_count", 0),
                            "phase": prev_state.get("phase", "planning")
                        }
                        yield sse_format({"type": "status", "message": f"Resuming session (phase: {initial_state['phase']})"})
                    else:
                        # New session
                        initial_state = {
                            "messages": [HumanMessage(content=user_message)],
                            "tool_calls": [],
                            "job_id": None,
                            "job_status": "pending",
                            "poll_count": 0,
                            "phase": "planning"
                        }
                    
                    config = {
                        "configurable": {
                            "session": session,
                            "llm_with_tools": llm_with_tools,
                            "thread_id": session_id
                        },
                        "recursion_limit": 100
                    }
                    
                    yield sse_format({"type": "status", "message": "Starting agent..."})
                    
                    final_state = None
                    
                    # Stream graph execution
                    async for event in graph.astream(initial_state, config=config, stream_mode="updates"):
                        for node_name, node_output in event.items():
                            final_state = node_output
                            
                            if node_name == "reasoner":
                                messages = node_output.get("messages", [])
                                phase = node_output.get("phase", "planning")
                                
                                for msg in messages:
                                    if hasattr(msg, "content") and msg.content:
                                        yield sse_format({
                                            "type": "thinking",
                                            "node": node_name,
                                            "content": msg.content[:500],
                                            "phase": phase
                                        })
                                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                                        for tc in msg.tool_calls:
                                            yield sse_format({
                                                "type": "tool_call",
                                                "tool": tc["name"],
                                                "args": tc["args"]
                                            })
                            
                            elif node_name == "tool_executor":
                                tool_calls = node_output.get("tool_calls", [])
                                for tc in tool_calls:
                                    result_preview = str(tc.get("result", ""))[:300]
                                    yield sse_format({
                                        "type": "tool_result",
                                        "tool": tc["name"],
                                        "result": result_preview
                                    })
                                
                                job_id = node_output.get("job_id")
                                if job_id:
                                    yield sse_format({
                                        "type": "job_created",
                                        "job_id": job_id
                                    })
                    
                    # Save session state for continuation
                    if final_state:
                        sessions[session_id] = {
                            "messages": initial_state["messages"] + final_state.get("messages", []),
                            "tool_calls": final_state.get("tool_calls", []),
                            "job_id": final_state.get("job_id"),
                            "job_status": final_state.get("job_status", "pending"),
                            "poll_count": final_state.get("poll_count", 0),
                            "phase": final_state.get("phase", "planning")
                        }
                        
                        # Check if awaiting confirmation
                        if final_state.get("phase") == "awaiting_confirmation":
                            yield sse_format({
                                "type": "awaiting_confirmation",
                                "message": "Agent is waiting for your confirmation to proceed."
                            })
                    
                    yield sse_format({"type": "complete", "message": "Agent finished"})
                    
        except Exception as e:
            import traceback
            yield sse_format({"type": "error", "message": str(e), "traceback": traceback.format_exc()})
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.delete("/session/{session_id}")
async def delete_session(session_id: str):
    """Clear a session to start fresh."""
    if session_id in sessions:
        del sessions[session_id]
        return {"status": "deleted"}
    return {"status": "not_found"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
