
from typing import Union, List, Optional
from pydantic import BaseModel
import sys
import os
sys.path.append(os.getcwd())
try:
    from mcp_server_py.models import SamplerColumnConfig, SamplerType, UUIDSamplerParams, PersonSamplerParams, CategorySamplerParams
except ImportError as e:
    print(f"Error importing modules: {e}")
    sys.exit(1)

def test_pydantic_union():
    # 1. Create a UUID Sampler
    uuid_col = SamplerColumnConfig(
        name="id",
        sampler_type=SamplerType.UUID,
        params=UUIDSamplerParams()
    )
    
    print(f"Original Params Type: {type(uuid_col.params)}")
    print(f"Dumped: {uuid_col.model_dump(exclude_none=True)}")
    
    # 2. Check if UUIDParams can be coerced to PersonParams
    # If PersonParams is first in Union, and accepts empty input (defaults), Pydantic might choose it?
    
    # 3. Print the params field info
    print("\nUnion choices:", SamplerColumnConfig.model_fields['params'].annotation)

if __name__ == "__main__":
    test_pydantic_union()
