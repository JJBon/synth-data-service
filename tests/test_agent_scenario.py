
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langgraph.agent import create_graph
import json

@pytest.mark.asyncio
async def test_full_user_story_scenario():
    """
    Test a complete user story using the new async create_graph API:
    - User wants invoice data.
    - Agent clarifies and defines schema.
    - Job is submitted.
    - User approves result.
    """

    # --- SETUP MOCKS ---

    # 1. Mock Session and Client
    mock_session = MagicMock()
    mock_client = MagicMock()
    mock_session.client = mock_client
    # IMPORTANT: call_tool is awaited in tool_executor_node, so it must be AsyncMock
    mock_session.call_tool = AsyncMock()
    
    # Mock implementation of call_tool to mirror args back as result
    # This simulates the MCP server returning the created config object
    async def mock_call_tool_impl(name, arguments):
        mock_res = MagicMock()
        # For define_ functions, return the args as the 'config'
        # We need to wrap it in a structure that looks like MCP content
        
        # Ensure 'name' is in the result for col configs if strictly required by agent.py logic
        # (agent.py uses c.get("name"))
        
        # Create a mock content object
        content_obj = MagicMock()
        content_obj.text = json.dumps(arguments) # Return args as JSON string
        mock_res.content = [content_obj]
        return mock_res
        
    mock_session.call_tool.side_effect = mock_call_tool_impl
    
    # Mock submit_job response
    mock_response = MagicMock()
    mock_response.job_id = "job_123"
    mock_response.status = "completed"
    mock_response.download_url = "http://nemo/data.json"
    mock_response.data = [{"col": "val"}]
    mock_client.submit_job.return_value = mock_response

    # 2. Mock LLM with Tools
    # `llm_with_tools` is what invoke() is called on in the reasoner node
    mock_llm_with_tools = MagicMock()
    # IMPORTANT: The code calls await llm.ainvoke, so specific mocking of ainvoke is needed
    mock_llm_with_tools.ainvoke = AsyncMock() 

    # --- DEFINE LLM RESPONSES ---

    # Response 1: Clarification Question (from Reasoner)
    resp_1 = AIMessage(content="Could you specify the columns?")

    # Response 2: Tool Definitions (Model + Columns) (from Reasoner)
    tool_call_1 = {
        "name": "add_model_config",
        "args": {"alias": "invoice_model", "model": "gpt-4o", "provider": "litellm"},
        "id": "call_1"
    }
    tool_call_2 = {
        "name": "add_llm_text_column",
        # NOTE: Updated param 'prompt' to match Pydantic model
        "args": {"name": "invoice_desc", "model_alias": "invoice_model", "prompt": "Generate invoice"},
        "id": "call_2"
    }
    # Note: New agent logic might require reasoning text + tool calls, or just tool calls.
    resp_2 = AIMessage(content="Defining schema...", tool_calls=[tool_call_1, tool_call_2])

    # Response 3: Finalize Submission (from Reasoner)
    tool_call_3 = {
        "name": "create_job",
        "args": {"job_name": "invoice_job", "num_records": 5},
        "id": "call_3"
    }
    resp_3 = AIMessage(content="Submitting...", tool_calls=[tool_call_3])
    
    # Response 4: Analyzer Summary (from Analyzer)
    # Note: Analyzer uses a different LLM instance in `agent.py`? 
    # In `create_graph`, `analyzer` node uses `llm` (not bound to tools).
    # But `create_graph` takes `llm_with_tools` as arg.
    # Typically `llm_with_tools` also behaves like an LLM.
    resp_4 = AIMessage(content="The data looks realistic with valid amounts.")

    # Side effects sequence:
    # 1. Reasoner -> resp_1 (Clarify)
    # 2. Reasoner -> resp_2 (Tools)
    # 3. Reasoner -> resp_3 (Finalize)
    # 4. Analyzer -> resp_4
    # Note: We mock ainvoke, prompting side effects
    mock_llm_with_tools.ainvoke.side_effect = [resp_1, resp_2, resp_3, resp_4]

    # --- BUILD GRAPH ---
    graph = await create_graph(mock_session, mock_llm_with_tools)

    # --- RUN GRAPH ---
    # We simulate the loop or just invoke with initial state using a mock "input" function if needed.
    # However, `human_input_node` uses `input()`. We need to patch that.
    
    with patch("builtins.input", side_effect=["I need invoices", "yes"]) as mock_input:
         # Initial invocation
         # The graph expects a list of messages
         initial_state = {"messages": [HumanMessage(content="Start generation")]}
         
         # Since we are using an async graph with async nodes, we MUST use ainvoke.
         # We also need to pass the dependencies via config, same as run_agent does.
         
         config = {"configurable": {"session": mock_session, "llm_with_tools": mock_llm_with_tools}}
         
         try:
            result = await graph.ainvoke(initial_state, config=config)
         except (StopIteration, RuntimeError):
            # This is expected when mocks run out of side effects
            pass

    # --- VERIFY ---
    
    # 1. Verify LLM calls (on ainvoke)
    assert mock_llm_with_tools.ainvoke.call_count >= 3
    
    # 2. Verify Client calls (Job Submission)
    # The `submitter` node NO LONGER calls `client.submit_job` directly.
    # It relies on the MCP tool execution.
    # So we check if `call_tool` was called with 'create_job'.
    
    # We can check the mock_session.call_tool args
    tool_calls = mock_session.call_tool.call_args_list
    # print(tool_calls)
    
    create_job_called = False
    for call in tool_calls:
        # call.args[0] is name, call.args[1] is arguments (implied positional or kwargs)
        # call_tool(name, arguments=...)
        args, kwargs = call
        if args[0] == "create_job":
            create_job_called = True
            assert kwargs['arguments']['job_name'] == "invoice_job"
            break
            
    assert create_job_called, "create_job tool was not called via MCP session"

    print("Async Scenario test passed!")

