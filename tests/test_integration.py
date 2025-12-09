import os
import time
import json
import pytest
from mcp_server_py.client import NemoDataDesignerClient
from mcp_server_py.models import SubmitJobRequest, ModelConfig, SamplerColumnConfig, SamplerType, CategorySamplerParams

@pytest.mark.integration
def test_integration():
    """
    Integration test to run against a local NeMo Data Designer server.
    Requires NEMO_DATA_DESIGNER_URL to be set or defaults to localhost:8080.
    """
    url = os.environ.get("NEMO_DATA_DESIGNER_URL", "http://localhost:8080")
    print(f"Connecting to NeMo Data Designer at {url}...")
    
    client = NemoDataDesignerClient(base_url=url)
    
    # Define a simple job
    req = SubmitJobRequest(
        job_name=f"integration_test_{int(time.time())}",
        model_configs=[
            ModelConfig(
                alias="gpt-test", 
                model="meta/llama3-8b-instruct", 
                provider="nvidiabuild" # Adjust as needed for local setup
            ).model_dump() # Client expects models but let's be safe if using pydantic
        ],
        column_configs=[
            SamplerColumnConfig(
                name="category_col",
                sampler_type=SamplerType.CATEGORY,
                params=CategorySamplerParams(values=["A", "B", "C"])
            ).model_dump()
        ],
        num_samples=5
    )
    
    # Note: `model_dump()` above is technically redundant if SubmitJobRequest expects objects, 
    # but based on my client implementation `request.model_configs` acts on the list.
    # Wait, SubmitJobRequest expects `List[ModelConfig]`.
    # So I should pass objects, not dicts.
    
    req_objects = SubmitJobRequest(
        job_name=f"integration_test_{int(time.time())}",
        model_configs=[
            ModelConfig(
                alias="gpt-test", 
                model="meta/llama3-8b-instruct", 
                provider="nvidiabuild"
            )
        ],
        column_configs=[
            SamplerColumnConfig(
                name="category_col",
                sampler_type=SamplerType.CATEGORY,
                params=CategorySamplerParams(values=["A", "B", "C"])
            )
        ],
        num_samples=5
    )

    try:
        print("Submitting job...")
        response = client.submit_job(req_objects)
        print(f"Job Submitted! ID: {response.job_id}")
        
        print("Results:")
        print(json.dumps(response.data, indent=2))
        
        print("\nIntegration Test PASSED!")
        
    except Exception as e:
        print(f"\nIntegration Test FAILED: {e}")
        if hasattr(e, 'response') and e.response:
             print(f"Server Response: {e.response.text}")
        pytest.fail(f"Integration test failed: {e}")

if __name__ == "__main__":
    test_integration()
