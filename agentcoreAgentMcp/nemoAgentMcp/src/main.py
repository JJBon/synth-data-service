import os
import sys
import json
import asyncio
import operator
import uuid
from typing import TypedDict, Annotated, List, Dict, Any, Optional

from langchain_core.messages import HumanMessage, AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.exceptions import OutputParserException
from langgraph.graph import StateGraph, END, START
from bedrock_agentcore import BedrockAgentCoreApp, BedrockAgentCoreContext
from langgraph.checkpoint.memory import MemorySaver
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SummaryStrategy

# Local project imports
from mcp_client.client import get_streamable_http_mcp_client as deployed_get_tools
from model.load import load_model

if os.getenv("LOCAL_DEV") == "1":
    try:
        from mcp_client.local import get_local_mcp_client as get_tools
    except ImportError:
        print("WARNING: mcp_client.local not found, falling back to empty mock")
        class MockClient:
            async def get_tools(self): return []
        
        def get_tools_mock():
            return MockClient()
        
        get_tools = get_tools_mock
else:
    get_tools = deployed_get_tools

# Instantiate model
llm = load_model()

# Import AgentCore Gateway as Streamable HTTP MCP Client
mcp_client = get_tools()


# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Initialize Memory safely
memory_session_manager = None
try:
    memory_manager = MemoryManager(region_name=os.getenv("AWS_REGION", "us-east-1"))
    # Single user constant
    SINGLE_USER_ID = "single_user"
    
    memory_resource = memory_manager.get_or_create_memory(
        name="LangGraphSingleUserMemoryNemo",
        description="Memory for single-user LangGraph agent conversations.",
        strategies=[
            SummaryStrategy(
                name="ConversationSummarizer",
                namespaces=[f"/summaries/{SINGLE_USER_ID}/{{sessionId}}"]
            )
        ]
    )
    
    memory_id = memory_resource.get('id')
    memory_session_manager = MemorySessionManager(memory_id=memory_id)
except Exception as e:
    print(f"WARNING: Global memory initialization failed (likely no AWS creds). Memory will be disabled. Error: {e}")
    SINGLE_USER_ID = "single_user" # fallback constraint

langgraph_memory = MemorySaver()


# --- State Definition (from agent.py) ---
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
    
    # Updated prompt from langgraph/agent.py
    system_prompt_content = f"""
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
"""
    system_prompt = SystemMessage(content=system_prompt_content)

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
    
    return {"messages": [response]}


async def tool_executor_node(state: DesignState, config):
    """
    Executes MCP tools.
    Adapted for AgentCore runtime where we have 'tools' list, not raw session.
    """
    print("\n--- EXECUTING TOOLS ---")
    messages = state["messages"]
    last_message = messages[-1]
    
    # We expect tools_map to be passed in config
    tools_map = config["configurable"]["tools_map"]
    
    tool_results = []
    function_calls = []

    if not last_message.tool_calls:
        return {"messages": []}

    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        args = tool_call["args"]
        print(f"Calling: {tool_name}")
        print(f"  Args: {json.dumps(args, indent=2)}")

        try:
             # Prevent excessive polling
            if tool_name == "get_job_status":
                print("  (Sleeping for 5s to avoid rate limits...)")
                await asyncio.sleep(5)

            # Execution Logic
            if tool_name in tools_map:
                # Execute the tool
                # We use .invoke or .run depending on tool type. LangChain tools usually support .invoke
                tool_instance = tools_map[tool_name]
                
                # IMPORTANT: We need to sanitize the RESULT of the tool invocation too, 
                # similar to what main.py did with SanitizedTool wrapper.
                # Or we can just trust the SanitizedTool wrapper if we wrapped them before passing to map.
                
                raw_result = await tool_instance.ainvoke(args)
                
                # Stringify mechanism (similar to SanitizedTool logic)
                output_str = str(raw_result) 
                # (You might want to improve this stringification if SanitizedTool logic was critical 
                # for recursively stripping IDs. If we wrap tools BEFORE putting in map, we are good.)

            else:
                output_str = f"Error: Tool {tool_name} not found."

            # Debug / logging
            # Try parsing JSON result
            try:
                res_obj = json.loads(output_str)
            except:
                res_obj = output_str

            print(f"  Result: {str(output_str)[:200]}..." if len(output_str) > 200 else f"  Result: {output_str}")
            
            tool_results.append(ToolMessage(tool_call_id=tool_call["id"], content=output_str))
            
            # Store config for submitter logic tracking
            function_calls.append({"name": tool_name, "args": args, "result": res_obj})
            
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
    
    # Check if create_job was in the tool calls
    job_created = False
    
    for call in state["mpc_tool_calls"]:
        if call.get("name") == "create_job":
            job_created = True
            created_job_details = call.get("result", {})
            break
            
    if job_created:
        print("Job submitted via MCP SDK.")
        msg = f"Job successfully submitted. Details: {created_job_details}"
        # Align with langgraph/agent.py: return AIMessage
        return {
             "job_status": "success",
             "messages": [AIMessage(content=msg)]
        }
    else:
        # Fallback if routed here but no job created (shouldn't happen with correct routing)
        return {
             "messages": [AIMessage(content="Job configuration updated.")]
        }


# We remove human_input_node for this AgentCore version, 
# as AgentCore is typically request/response via invoke.

# --- Main Entrypoint ---

@app.entrypoint
async def invoke(payload, context: BedrockAgentCoreContext):
    print("DEBUG: [VERSION] 2.0.0 - Custom Graph Port")
    session_id = context.session_id or payload.get("session_id")

    if session_id is not None:
        # session_id provided - validate it
        if len(session_id) < 33:
            return {
                "error": "session_id must be at least 33 characters long",
                "provided_length": len(session_id),
                "required_length": 33
            }
    else:
        # No session_id provided - generate one
        session_id = f"user-single-conversation-{str(uuid.uuid4())}"

    config = {"configurable": {"thread_id": session_id}}
    
    # 1. Load MCP Tools
    raw_tools = await mcp_client.get_tools()
    
    
    # 1.5 NeMo Connection Check & System Prompt Injection
    system_status_msg = "NeMo Service Status: Unknown"
    
    health_tool = next((t for t in raw_tools if t.name == "check_service_health"), None)
    if health_tool:
        try:
            print("DEBUG: Checking NeMo Service Health...")
            # health_tool is a LangChain tool, supports ainvoke
            health_res = await health_tool.ainvoke({})
            # Result is dict usually, or string if sanitized? Local tools return what function returns.
            # Local client wraps with @tool, so it returns dict.
            status = health_res.get("status", "unknown")
            if status == "connected":
                 system_status_msg = f"SYSTEM NOTIFICATION: NeMo Data Designer Service is CONNECTED. {health_res.get('details', '')}"
            else:
                 msg = health_res.get("message", "Unknown error")
                 system_status_msg = f"SYSTEM NOTIFICATION: CRITICAL - NeMo Data Designer Service is UNREACHABLE. Error: {msg}. You may verify schema but CANNOT generate data."
        except Exception as e:
             system_status_msg = f"SYSTEM NOTIFICATION: CRITICAL - NeMo Service Health Check Failed. Error: {e}"
    
    print(f"DEBUG: {system_status_msg}")

    # 2. Wrap/Sanitize Tools
    from langchain_core.tools import BaseTool
    
    class SanitizedTool(BaseTool):
        wrapped_tool: BaseTool
        
        def __init__(self, tool: BaseTool):
            super().__init__(
                name=tool.name,
                description=tool.description,
                args_schema=tool.args_schema,
                wrapped_tool=tool
            )
            
        def _run(self, *args, **kwargs) -> Any:
            # Sync call - mcp tools are typically async
            return self.wrapped_tool.run(*args, **kwargs)
            
        async def _arun(self, *args, **kwargs) -> Any:
            try:
                # Use ainvoke with kwargs to get the content
                result = await self.wrapped_tool.ainvoke(kwargs)
                print(f"DEBUG: [TOOL_CALL] {self.name} args={kwargs} -> raw_result={result}")
                
                # Aggressively clean and flatten results for Bedrock Converse API
                def clean(obj):
                    # Handle MCP/Pydantic models which are NOT dicts
                    if hasattr(obj, "model_dump"):
                        obj = obj.model_dump()
                    elif hasattr(obj, "dict"):
                        obj = obj.dict()

                    if isinstance(obj, list):
                        # Join multiple text parts into one string for simplicity and safety
                        text_parts = []
                        for item in obj:
                            c = clean(item)
                            if isinstance(c, str):
                                text_parts.append(c)
                            elif isinstance(c, dict) and "text" in c:
                                text_parts.append(str(c["text"]))
                            else:
                                text_parts.append(str(c))
                        return "\n".join(text_parts)
                    
                    if isinstance(obj, dict):
                        # Bedrock Converse API doesn't allow 'id' in text content blocks
                        # If this is a text block, flatten it to just the string
                        if "text" in obj:
                            val = obj["text"]
                            if isinstance(val, dict):
                                return val.get("text", str(val))
                            return str(val)
                        
                        # Strip 'id' from any remaining dictionary components
                        return {k: clean(v) for k, v in obj.items() if k != "id"}
                    
                    return obj

                sanitized_result = clean(result)
                print(f"DEBUG: [TOOL_RESULT] {self.name} -> sanitized={sanitized_result}")
                return str(sanitized_result) # Final safety: force to string
            except Exception as e:
                print(f"DEBUG: [TOOL_ERROR] Error in tool {self.name}: {e}")
                raise

    files_tools = [SanitizedTool(t) for t in raw_tools]
    tools_map = {t.name: t for t in files_tools}
    
    # 3. Bind to LLM
    llm_with_tools = llm.bind_tools(files_tools)
    
    # 4. Define Graph
    workflow = StateGraph(DesignState)
    workflow.add_node("reasoner", reasoner_node)
    workflow.add_node("tool_executor", tool_executor_node)
    workflow.add_node("submitter", submitter_node)
    
    
    def should_continue(state):
        last = state["messages"][-1]
        if last.tool_calls:
            return "tool_executor"
        return END 
                   
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
        END: END
    })
    
    # Conditional edge from tool_executor
    workflow.add_conditional_edges("tool_executor", route_after_tools, {
        "submitter": "submitter",
        "reasoner": "reasoner"
    })
    
    # Submitter ends the turn (returns response to user)
    workflow.add_edge("submitter", END)

    
    graph = workflow.compile(checkpointer=langgraph_memory)
    
    # --- Logic Reordered: Check History & Memory ---
    
    # Check if LangGraph has existing conversation history
    try:
        current_state = await graph.aget_state(config)
        existing_messages = current_state.values.get("messages", []) if current_state and current_state.values else []
        has_existing_history = len(existing_messages) > 0
        print(f"DEBUG: Found {len(existing_messages)} existing messages in LangGraph memory.")
    except Exception as e:
        print(f"DEBUG: Failed to check graph state: {e}")
        has_existing_history = False

    # Get or create Bedrock memory session
    memory_session = None
    if memory_session_manager:
        try:
            memory_session = memory_session_manager.create_memory_session(
                actor_id=SINGLE_USER_ID,
                session_id=session_id
            )
            print(f"DEBUG: Bedrock Memory Session Created? {bool(memory_session)}")
            if memory_session:
                print(f"DEBUG: MemorySession Methods: {dir(memory_session)}")
        except Exception as e:
            print(f"DEBUG: Failed to create memory session: {e}")

    # 5. Run Graph
    prompt = payload.get("prompt", "What is Agentic AI?")
    human_message_content = prompt

    # If no LangGraph history, try to restore context from Bedrock memory
    if not has_existing_history and memory_session:
        try:
            await asyncio.sleep(1) # Allow Bedrock processing time
            # Try to get session-specific memory records
            session_namespace = f"/summaries/{SINGLE_USER_ID}/{session_id}"
            if hasattr(memory_session, 'list_long_term_memory_records'):
                memory_records = memory_session.list_long_term_memory_records(
                    namespace_prefix=session_namespace
                )
                
                # Extract context
                if memory_records and len(memory_records) > 0:
                    first_record = memory_records[0]
                    summary_text = ""
                    if hasattr(first_record, 'content'):
                        content_obj = first_record.content
                        if isinstance(content_obj, dict):
                            summary_text = content_obj.get('text', '').strip()
                        elif hasattr(content_obj, 'text'):
                            summary_text = content_obj.text.strip()
                    
                    if summary_text:
                        print(f"DEBUG: Restored context from memory: {summary_text[:50]}...")
                        human_message_content = f"Previous conversation context from this session:\n{summary_text}\n\nCurrent question: {prompt}"
        except Exception as e:
             print(f"DEBUG: Memory retrieval failed: {e}")

    initial_messages = [HumanMessage(content=human_message_content)]
    
    # But if we have no history, we MUST inject System Prompt.
    if not has_existing_history:
        initial_messages.insert(0, SystemMessage(content=system_status_msg))

    initial_state = {
        "messages": initial_messages,
        "mpc_tool_calls": [],
        "job_status": "pending"
    }
    
    # Update Config (Fix overwriting thread_id)
    config.update({
        "configurable": {
            "thread_id": session_id,
            "llm_with_tools": llm_with_tools, 
            "tools_map": tools_map
        }, 
        "recursion_limit": 50
    })
    
    result = await graph.ainvoke(initial_state, config=config)
    
    last_message = result["messages"][-1]
    ai_response = last_message.content

    # Store conversation in Bedrock memory
    if memory_session and hasattr(memory_session, 'add_turns'):
        try:
            print("DEBUG: Saving turns to Bedrock Memory...")
            user_msg = ConversationalMessage(prompt, MessageRole.USER)
            memory_session.add_turns(messages=[user_msg])
            
            assistant_msg = ConversationalMessage(ai_response, MessageRole.ASSISTANT)
            memory_session.add_turns(messages=[assistant_msg])
            print("DEBUG: Saved turns.")
        except Exception as e:
            print(f"DEBUG: Failed to save to memory: {e}")

    # Return last message content
    return {
        "result": ai_response
    }

if __name__ == "__main__":
    app.run()