import os
import asyncio
import uuid
from typing import TypedDict, List, Annotated
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langgraph.graph import StateGraph, END, add_messages
from langgraph.checkpoint.memory import MemorySaver
from bedrock_agentcore import BedrockAgentCoreApp, BedrockAgentCoreContext
from bedrock_agentcore_starter_toolkit.operations.memory.manager import MemoryManager
from bedrock_agentcore.memory.session import MemorySessionManager
from bedrock_agentcore.memory.constants import ConversationalMessage, MessageRole
from bedrock_agentcore_starter_toolkit.operations.memory.models.strategies import SummaryStrategy
from .mcp_client.client import get_streamable_http_mcp_client as deployed_get_tools
from .model.load import load_model

# Environment-based tool selection
if os.getenv("LOCAL_DEV") == "1":
    # In local dev, instantiate dummy MCP client so the code runs without deploying
    async def get_tools():
        return []
else:
    get_tools = deployed_get_tools

# Initialize components once at module level
llm = load_model()

# Integrate with Bedrock AgentCore
app = BedrockAgentCoreApp()

# Initialize Bedrock AgentCore Memory Manager
memory_manager = MemoryManager(region_name=os.getenv("AWS_REGION", "us-east-1"))

# Single user constant
SINGLE_USER_ID = "single_user"

# Create or get memory resource with strategies for single user
memory_resource = memory_manager.get_or_create_memory(
    name="LangGraphSingleUserMemory",
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

# Initialize LangGraph memory for immediate conversation history
langgraph_memory = MemorySaver()

# Define the state structure with proper message accumulation
class GraphState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

# Define the LLM node
async def llm_node(state: GraphState) -> GraphState:
    """Node that processes messages through the LLM."""
    messages = state["messages"]
    
    # Process all messages (including conversation history) through the LLM
    response = await llm.ainvoke(messages)
    return {"messages": [response]}

# Create the StateGraph
workflow = StateGraph(GraphState)

# Add nodes
workflow.add_node("llm", llm_node)

# Set entry point
workflow.set_entry_point("llm")

# Add edge from llm to END
workflow.add_edge("llm", END)

# Compile the graph with LangGraph memory for immediate history
graph = workflow.compile(checkpointer=langgraph_memory)

@app.entrypoint
async def invoke(payload, context: BedrockAgentCoreContext):
    """Process user prompt through LangGraph with persistent memory."""
    prompt = payload.get("prompt", "What is Agentic AI?")
    
    # Handle session_id - can come from context (CLI -s) or payload
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
    
    human_message = HumanMessage(content=prompt)
    config = {"configurable": {"thread_id": session_id}}
    
    # Check if LangGraph has existing conversation history
    try:
        current_state = await graph.aget_state(config)
        existing_messages = current_state.values.get("messages", []) if current_state and current_state.values else []
        has_existing_history = len(existing_messages) > 0
    except:
        has_existing_history = False
    
    # Get or create Bedrock memory session
    memory_session = None
    try:
        memory_session = memory_session_manager.create_memory_session(
            actor_id=SINGLE_USER_ID,
            session_id=session_id
        )
    except:
        pass
    
    # If no LangGraph history, try to restore context from Bedrock memory
    if not has_existing_history and memory_session:
        try:
            await asyncio.sleep(1)  # Allow Bedrock processing time
            
            # Try to get session-specific memory records
            session_namespace = f"/summaries/{SINGLE_USER_ID}/{session_id}"
            memory_records = None
            
            if hasattr(memory_session, 'list_long_term_memory_records'):
                memory_records = memory_session.list_long_term_memory_records(
                    namespace_prefix=session_namespace
                )
            
            # Extract context from memory records
            if memory_records and len(memory_records) > 0:
                first_record = memory_records[0]
                summary_text = ""
                
                # Handle MemoryRecord objects
                if hasattr(first_record, 'content'):
                    content_obj = first_record.content
                    if isinstance(content_obj, dict):
                        summary_text = content_obj.get('text', '').strip()
                    elif hasattr(content_obj, 'text'):
                        summary_text = content_obj.text.strip()
                
                # Enhance message with context if found
                if summary_text:
                    enhanced_content = f"Previous conversation context from this session:\n{summary_text}\n\nCurrent question: {prompt}"
                    human_message = HumanMessage(content=enhanced_content)
                    
        except:
            pass  # Continue without context if memory retrieval fails
    
    # Invoke LangGraph
    result = await graph.ainvoke({"messages": [human_message]}, config=config)
    last_message = result["messages"][-1]
    ai_response = last_message.content
    
    # Store conversation in Bedrock memory
    if memory_session and hasattr(memory_session, 'add_turns'):
        try:
            user_msg = ConversationalMessage(prompt, MessageRole.USER)
            memory_session.add_turns(messages=[user_msg])
            
            assistant_msg = ConversationalMessage(ai_response, MessageRole.ASSISTANT)
            memory_session.add_turns(messages=[assistant_msg])
        except:
            pass  # Continue if memory storage fails
    
    return {
        "result": ai_response,
        "session_id": session_id
    }
if __name__ == "__main__":
    app.run()