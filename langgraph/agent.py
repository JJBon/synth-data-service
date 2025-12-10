
import sys
import os
import json
import time
import asyncio
from typing import TypedDict, Annotated, List, Dict, Any, Union, Literal, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from langgraph.graph import StateGraph, END, START
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field
import operator
import re
import uuid

# Import models for Type Checking / Robustness ensuring we can parse responses if needed
# (Though mostly we deal with Dicts from MCP)
from mcp_server_py.models import (
    ModelConfig, 
    SubmitJobRequest,
    InferenceParameters
)
from mcp_server_py.client import NemoDataDesignerClient

# MCP Imports
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client

# --- State Definition ---
class DesignState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    mpc_tool_calls: Annotated[List[Dict[str, Any]], operator.add] # Accumulates tool configs
    final_job_id: str
    generated_data: str
    download_url: str
    user_feedback: str
    job_status: str

# --- Graph Nodes ---

async def reasoner_node(state: DesignState, config):
    """
    The brain of the agent. Decides to ask questions or call tools.
    """
    print("\n--- REASONER ---")
    messages = state["messages"]
    llm_with_tools = config["configurable"]["llm_with_tools"]
    session_id = config["configurable"].get("thread_id")

    system_prompt = SystemMessage(content=f"""
You are an expert Data Designer AI. Your goal is to help the user design a synthetic dataset generation job.
You interact with a NeMo Data Designer Service via tools.
You are operating in session: {session_id}

PROCESS:
1. GATHER REQUIREMENTS.
2. DEFINE MODEL FIRST: You MUST call `add_model_config` before any LLM columns.
3. DISCOVER SCHEMA: Call tools to define columns.
4. FINALIZE: Call `finalize_submission` when ready. You MUST pass session_id='{session_id}'
5. MONITOR & IMPORT: After submission, check job status. When 'COMPLETED', AUTOMATICALLY call `import_results` with session_id='{session_id}'.

CRITICAL RULES:
- ALWAYS call `add_model_config` FIRST if you plan to use LLM columns (add_llm_text_column).
- For simple datasets without LLM text, you don't need a model.
- Use `add_category_column` for known lists (Status, Currency, etc.).
- Use `add_int_column` / `add_float_column` for numbers.
- Use `add_person_column` for realistic names (Customer Name).
- Use `add_uuid_column` for unique IDs.
- Use `add_datetime_column` for dates.
- Use `add_llm_text_column` ONLY if you have defined a model first.
- NO SIMULATION. Call the tools.
- IMPORTANT: Use 'snake_case' for column names (e.g., 'short_description', not 'Short Description') to avoid template errors.
- If referencing another column in a prompt, use the exact snake_case name (e.g., '{{ short_description }}').
- ON COMPLETION: If a job is 'COMPLETED', you MUST call `import_results(job_id)` to show the data in the UI.

When the user says "submit", call `finalize_submission`.
Then track status until 'COMPLETED' and import results.
""")

    if not any(isinstance(m, SystemMessage) for m in messages):
        all_messages = [system_prompt] + messages
    else:
        all_messages = messages

    print(f"DEBUG: Calling LLM with {len(all_messages)} messages...")
    try:
        response = await llm_with_tools.ainvoke(all_messages)
        print(f"DEBUG: LLM response received.")
    except Exception as e:
        print(f"DEBUG: LLM call failed: {e}")
        raise
    
    if response.content:
        print(f"\n[LLM]: {response.content}")
    
    if response.tool_calls:
        print(f"DEBUG: LLM requested {len(response.tool_calls)} tool calls.")

    return {"messages": [response]}

async def tool_executor_node(state: DesignState, config):
    """
    Executes MCP tools.
    """
    print("\n--- EXECUTING TOOLS ---")
    messages = state["messages"]
    last_message = messages[-1]
    
    session = config["configurable"]["session"]
    
    tool_results = []
    function_calls = []

    if not last_message.tool_calls:
        return {"messages": []}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        print(f"Calling: {tool_name}")
        print(f"  Args: {json.dumps(args, indent=2)}")

        # Special handling for finalize_submission: just accumulate argument, don't necessarily need MCP if logic is local
        # BUT user wanted everything on MCP. So we call MCP tool, and use its result.
        
        try:
             # Prevent excessive polling
            if tool_name == "get_job_status":
                print("  (Sleeping for 10s to avoid rate limits...)")
                await asyncio.sleep(10)

             # Call MCP Tool
            result = await session.call_tool(tool_name, arguments=args)
            
            # Extract Text Content
            output_str = ""
            if result.content:
                for c in result.content:
                    if hasattr(c, "text"):
                        output_str += c.text
            
            # Try parsing JSON result (Config object)
            try:
                res_obj = json.loads(output_str)
            except:
                res_obj = output_str

            print(f"  Result: {str(output_str)[:200]}..." if len(output_str) > 200 else f"  Result: {output_str}")
            
            tool_results.append(ToolMessage(tool_call_id=tool_call["id"], content=output_str))
            
            # Store config for submitter
            function_calls.append({"name": tool_name, "result": res_obj, "args": args})

        except Exception as e:
            print(f"Error executing {tool_name}: {e}")
            tool_results.append(ToolMessage(tool_call_id=tool_call["id"], content=f"Error: {e}"))

    return {
        "messages": tool_results,
        "mpc_tool_calls": function_calls
    }

async def submitter_node(state: DesignState, config):
    """
    Submits the final job.
    """
    print("\n--- SUBMITTING JOB ---")
    
    # If create_job was called via MCP, the job is already running/submitted on the server.
    # We just need to verify the result or notify the user.
    
    # Check if create_job was in the tool calls
    job_created = False
    created_job_details = {}
    
    for call in state["mpc_tool_calls"]:
        if call.get("name") == "create_job":
            job_created = True
            created_job_details = call.get("result", {})
            break
            
    if job_created:
        # In SDK mode, create_job returns the job status/ID.
        # We can assume success if the tool call didn't error.
        print("Job submitted via MCP SDK.")
        msg = f"Job successfully submitted via SDK. Details: {created_job_details}"
        return {
             "job_status": "success", 
             "messages": [AIMessage(content=msg)]
        }
    else:
        # Legacy fallback (only if create_job wasn't called but finalize_submission was?)
        # For now, just assume if we are here, we might need to finalize?
        # But if the user wants SDK priority, we should rely on the tool execution.
        print("Warning: create_job tool was not detected in recent calls.")
        return {
            "messages": [AIMessage(content="Job configuration updated.")]
        }

async def human_input_node(state: DesignState, config):
    print("\n(USER INPUT REQUIRED)")
    loop = asyncio.get_running_loop()
    # Blocking input
    user_input = await loop.run_in_executor(None, input, "User: ")
    if user_input.lower() in ["q", "quit"]:
        sys.exit(0)
    return {"messages": [HumanMessage(content=user_input)]}

# --- Main Graph Runner ---


# ... (Imports remain the same) ...

async def create_graph(session, llm_with_tools):
    # 4. Define Graph
    workflow = StateGraph(DesignState)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("human_input", human_input_node)
    workflow.add_node("submitter", submitter_node)
    
    def should_continue(state):
        last = state["messages"][-1]
        if last.tool_calls:
                if any(t["name"] == "finalize_submission" for t in last.tool_calls):
                    return "submitter" # Actually, we exec tool first, then submit?
                    # Better: tool_executor handles finalize call (gets args), then we see if finalize was called.
                return "tool_executor"
        return "human_input"
    
    def check_submission(state):
            # After submission, go back to input or end?
            return "human_input"

    def route_after_tools(state):
        calls = state["mpc_tool_calls"]
        if calls:
             last_call = calls[-1]["name"]
             if last_call == "finalize_submission" or last_call == "create_job":
                return "submitter"
        return "reasoner"

    workflow.add_edge(START, "reasoner")
    workflow.add_conditional_edges("reasoner", should_continue, {
        "tool_executor": "tool_executor",
        "human_input": "human_input",
        "submitter": "tool_executor" # Route via tool executor to capture args first
    })
    workflow.add_conditional_edges("tool_executor", route_after_tools, {
        "submitter": "submitter",
        "reasoner": "reasoner"
    })
    
    workflow.add_edge("submitter", "human_input")
    workflow.add_edge("human_input", "reasoner")
    
    return workflow.compile()

async def run_agent():
    # 1. Connect to MCP
    url = "http://localhost:8002/sse"
    print(f"Connecting to MCP at {url}...")
    
    async with sse_client(url) as streams:
        async with ClientSession(streams[0], streams[1]) as session:
            await session.initialize()
            
            # 2. Discover Tools
            tools_list = await session.list_tools()
            print(f"Discovered {len(tools_list.tools)} tools.")
            
            # 3. Bind to LLM
            # ... (Tool formatting logic same as before) ...
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
            print(f"Using Model: {model_name}")
            llm = ChatOpenAI(model=model_name, temperature=0, base_url="http://localhost:4000/v1", api_key=os.environ.get("LITELLM_KEY", "sk-placeholder"))
            llm_with_tools = llm.bind_tools(formatted_tools)

            graph = await create_graph(session, llm_with_tools)
            
            print("Agent Ready!")
            # Start with a user greeting to trigger the conversation
            initial_message = HumanMessage(content="Hello! I want to generate synthetic data. Please help me.")
            initial_state = {"messages": [initial_message], "mpc_tool_calls": []}
            
            # Pass session and llm via config
            config = {"configurable": {"session": session, "llm_with_tools": llm_with_tools}, "recursion_limit": 100}
            
            print("Starting graph...")
            await graph.ainvoke(initial_state, config=config)

if __name__ == "__main__":
    asyncio.run(run_agent())
