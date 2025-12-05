import sys
import os

# Add root directory to sys.path to allow importing mcp_server_py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from typing import TypedDict, Annotated, List, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
import operator

# Import from the package
from mcp_server_py.server import (
    create_model_config,
    create_category_sampler,
    create_llm_text_column,
    create_score,
    create_llm_judge_column,
    submit_job
)

class DesignState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    model_configs: List[Dict[str, Any]]
    column_configs: List[Dict[str, Any]]
    scores: List[Dict[str, Any]]
    job_id: str

def planner_node(state: DesignState):
    print("--- PLANNER ---")
    return {
        "messages": [AIMessage(content="Planning to create a QA dataset with accuracy judging.")]
    }

def tool_node(state: DesignState):
    print("--- EXECUTING TOOLS ---")
    
    # 1. Create Model
    model = create_model_config(
        alias="gpt4",
        model="gpt-4",
        provider="openai"
    )
    
    # 2. Create Category Sampler
    category = create_category_sampler(
        name="topic",
        values=["Science", "History", "Arts"]
    )
    
    # 3. Create LLM Text Column (Question)
    question = create_llm_text_column(
        name="question",
        model_alias="gpt4",
        prompt_template="Generate a question about {{ topic }}."
    )
    
    # 4. Create LLM Text Column (Answer)
    answer = create_llm_text_column(
        name="answer",
        model_alias="gpt4",
        prompt_template="Answer this question: {{ question }}"
    )
    
    # 5. Create Score
    acc_score = create_score(
        name="Accuracy",
        description="Is it correct?",
        options={"Yes": "Correct", "No": "Wrong"}
    )
    
    # 6. Create Judge
    judge = create_llm_judge_column(
        name="eval",
        model_alias="gpt4",
        prompt_template="Judge the answer.",
        scores=[acc_score]
    )
    
    return {
        "model_configs": [model],
        "column_configs": [category, question, answer, judge],
        "scores": [acc_score],
        "messages": [AIMessage(content="Tools executed. Configs generated.")]
    }

def submitter_node(state: DesignState):
    print("--- SUBMITTING JOB ---")
    
    result = submit_job(
        job_name="agent-test-job",
        model_configs=state["model_configs"],
        column_configs=state["column_configs"],
        num_samples=10
    )
    
    print(f"Submission Result: {result}")
    
    return {
        "messages": [AIMessage(content=result)],
        "job_id": result
    }

def run_agent():
    print("Starting Agent execution...")
    
    # Build Graph
    builder = StateGraph(DesignState)
    builder.add_node("planner", planner_node)
    builder.add_node("tools", tool_node)
    builder.add_node("submitter", submitter_node)
    builder.set_entry_point("planner")
    builder.add_edge("planner", "tools")
    builder.add_edge("tools", "submitter")
    builder.add_edge("submitter", END)
    
    graph = builder.compile()

    initial_state = {
        "messages": [HumanMessage(content="Create a QA dataset")],
        "model_configs": [],
        "column_configs": [],
        "scores": [],
        "job_id": ""
    }
    
    # Run the graph
    try:
        final_state = graph.invoke(initial_state)
        print(f"Job ID: {final_state['job_id']}")
        print(f"Final Message: {final_state['messages'][-1].content}")
    except Exception as e:
        print(f"Error running graph: {e}")

if __name__ == "__main__":
    run_agent()

