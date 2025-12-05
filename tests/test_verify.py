import pytest
import os

def test_imports_and_models():
    print("Importing models...")
    from mcp_server_py.models import DataDesignerConfig, SamplerType, ModelConfig, InferenceParameters
    print("Models imported successfully.")
    
    print("Importing server...")
    from mcp_server_py.server import mcp
    print("Server imported successfully.")
    
    # Test model instantiation
    print("Testing model instantiation...")
    
    m = ModelConfig(
        alias="test",
        model="gpt-4",
        inference_parameters=InferenceParameters()
    )
    print(f"Model created: {m.alias}")
    assert m.alias == "test"

