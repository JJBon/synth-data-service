import pytest
from mcp_server_py.models import Score, LLMJudgeColumnConfig

def test_judge_creation():
    print("Testing Score creation...")
    accuracy = Score(
        name="Accuracy",
        description="Factual correctness",
        options={"Accurate": "Correct", "Inaccurate": "Wrong"}
    )
    print(f"Score created: {accuracy.name}")
    assert accuracy.name == "Accuracy"

    print("Testing LLMJudgeColumnConfig...")
    judge = LLMJudgeColumnConfig(
        name="judge_column",
        model_alias="gpt4",
        prompt="Judge this.",
        scores=[accuracy]
    )
    print(f"Judge column created with {len(judge.scores)} scores.")
    assert len(judge.scores) == 1
    assert judge.scores[0].name == "Accuracy"

