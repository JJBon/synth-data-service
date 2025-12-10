"""Chat component that consumes SSE stream from LangGraph FastAPI server.
Supports multi-turn conversations with session management for human-in-the-loop.
"""
import streamlit as st
import requests
import json
import os
import uuid

LANGGRAPH_URL = os.environ.get("LANGGRAPH_SERVER_URL", "http://langgraph-server:8003")


def stream_agent_response(user_message: str, session_id: str = None):
    """
    Stream agent response via SSE from FastAPI server.
    Yields status updates as they arrive.
    Supports multi-turn with session_id for human-in-the-loop.
    """
    url = f"{LANGGRAPH_URL}/generate"
    
    payload = {"message": user_message}
    if session_id:
        payload["session_id"] = session_id
    
    try:
        response = requests.post(
            url,
            json=payload,
            stream=True,
            headers={"Accept": "text/event-stream"},
            timeout=300  # 5 min timeout for long jobs
        )
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    data_str = line_str[6:]
                    try:
                        data = json.loads(data_str)
                        yield data
                    except json.JSONDecodeError:
                        continue
                        
    except requests.RequestException as e:
        yield {"type": "error", "message": str(e)}


def render(on_job_complete=None):
    """Render the chat interface with SSE streaming and session management."""
    st.divider()
    st.subheader("💬 Chat with Agent")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "agent_activity" not in st.session_state:
        st.session_state.agent_activity = []
    
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    
    if "awaiting_confirmation" not in st.session_state:
        st.session_state.awaiting_confirmation = False
    
    # Reset button
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("🔄 New Chat"):
            # Clear session on server
            try:
                requests.delete(f"{LANGGRAPH_URL}/session/{st.session_state.session_id}")
            except:
                pass
            st.session_state.messages = []
            st.session_state.agent_activity = []
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.awaiting_confirmation = False
            st.rerun()
    
    # Scrollable chat history container
    with st.container(height=700):
        # Display chat history
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Display agent activity
        if st.session_state.agent_activity:
            with st.expander("🔧 Agent Activity", expanded=False):
                for activity in st.session_state.agent_activity[-30:]:
                    st.text(activity)
        
        # Show hint if awaiting confirmation
        if st.session_state.awaiting_confirmation:
            st.info("👆 The agent is waiting for your confirmation. Reply 'yes' to proceed or describe changes.")
    
    # Chat input
    if prompt := st.chat_input("Describe the data you want to generate..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Clear previous activity
        st.session_state.agent_activity = []
        st.session_state.awaiting_confirmation = False
        
        # Process with streaming
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            activity_placeholder = st.empty()
            
            final_response = ""
            job_id = None
            csv_path = None
            agent_content = ""
            
            with st.spinner("🤖 Agent is working..."):
                for event in stream_agent_response(prompt, st.session_state.session_id):
                    event_type = event.get("type", "unknown")
                    
                    # Capture session_id from server
                    if event_type == "session":
                        server_session_id = event.get("session_id", "")
                        if server_session_id:
                            st.session_state.session_id = server_session_id
                    
                    elif event_type == "status":
                        msg = event.get("message", "")
                        st.session_state.agent_activity.append(f"📌 {msg}")
                        status_placeholder.text(f"Status: {msg}")
                    
                    elif event_type == "thinking":
                        content = event.get("content", "")
                        phase = event.get("phase", "")
                        st.session_state.agent_activity.append(f"🤔 [{phase}] {content[:80]}...")
                        status_placeholder.text(f"Thinking ({phase})...")
                        agent_content = content  # Capture for display
                    
                    elif event_type == "tool_call":
                        tool = event.get("tool", "")
                        args = json.dumps(event.get("args", {}))[:60]
                        st.session_state.agent_activity.append(f"🔧 {tool}: {args}...")
                        status_placeholder.text(f"Calling {tool}...")
                    
                    elif event_type == "tool_result":
                        tool = event.get("tool", "")
                        result = event.get("result", "")[:80]
                        st.session_state.agent_activity.append(f"✓ {tool}: {result}...")
                        status_placeholder.text(f"✓ {tool} completed")
                        
                        # Extract csv_path from finalize_job result
                        if tool == "finalize_job":
                            full_result = event.get("result", "")
                            if "csv" in full_result and "/tmp/" in full_result:
                                import re
                                csv_match = re.search(r"'/tmp/data-designer-output/[^']+\.csv'", full_result)
                                if csv_match:
                                    csv_path = csv_match.group().strip("'")
                    
                    elif event_type == "job_created":
                        job_id = event.get("job_id", "")
                        st.session_state.agent_activity.append(f"📤 Job created: {job_id}")
                        status_placeholder.text(f"Job submitted: {job_id}")
                    
                    elif event_type == "awaiting_confirmation":
                        st.session_state.awaiting_confirmation = True
                        st.session_state.agent_activity.append("⏸️ Awaiting confirmation")
                    
                    elif event_type == "complete":
                        final_response = agent_content if agent_content else "✅ Agent completed!"
                        st.session_state.agent_activity.append("✅ Complete")
                    
                    elif event_type == "error":
                        error_msg = event.get("message", "Unknown error")
                        final_response = f"❌ Error: {error_msg}"
                        st.session_state.agent_activity.append(f"❌ {error_msg}")
                    
                    # Update activity display
                    with activity_placeholder.container():
                        for a in st.session_state.agent_activity[-5:]:
                            st.text(a)
            
            # Show final response
            if final_response:
                st.markdown(final_response)
                st.session_state.messages.append({"role": "assistant", "content": final_response})
            
            # Trigger callback if job completed and csv_path found
            if job_id and csv_path and on_job_complete:
                on_job_complete(job_id, csv_path)
        
        st.rerun()
