
import os
import sys
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langchain_core.tools import tool

os.environ["NVIDIA_API_KEY"] = os.environ.get("NIM_API_KEY", "")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from mcp_server_py.server import create_model_config

import pytest

pytestmark = pytest.mark.integration

def test_simple():
    print("Testing simple invoke...")
    llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")
    try:
        res = llm.invoke("Hello")
        print(f"Success: {res.content}")
    except Exception as e:
        print(f"Error simple: {e}")

def test_tools():
    print("\nTesting tool load...")
    @tool
    def sanity_check():
        """A simple tool."""
        return "ok"
    
    llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")
    llm2 = llm.bind_tools([sanity_check])
    try:
        res = llm2.invoke("Call the sanity check tool")
        print(f"Success tools: {res}")
    except Exception as e:
        print(f"Error tools: {e}")

def test_mcp_tool_binding():
    print("\nTesting MCP imported tool binding...")
    
    @tool
    def define_model_wrapper(alias: str, model: str):
        """Wrapper tool."""
        return create_model_config(alias, model)
    
    llm = ChatNVIDIA(model="meta/llama-3.1-70b-instruct")
    llm2 = llm.bind_tools([define_model_wrapper])
    try:
        res = llm2.invoke("Define a model called gpt4")
        print(f"Success wrapper: {res}")
    except Exception as e:
        print(f"Error wrapper: {e}")

if __name__ == "__main__":
    test_simple()
    test_tools()
    test_mcp_tool_binding()
