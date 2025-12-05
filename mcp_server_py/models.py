from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

class SamplerType(str, Enum):
    CATEGORY = "category"
    UNIFORM = "uniform"
    BERNOULLI = "bernoulli"
    INTEGER = "integer" # Assuming existence based on standard samplers, though not explicitly in snippet
    FLOAT = "float"

class InferenceParameters(BaseModel):
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 1024
    gpu_memory_utilization: float = 0.5
    tensor_parallel_size: int = 1
    
class ModelConfig(BaseModel):
    alias: str
    model: str
    provider: str = "nvidiabuild"
    inference_parameters: Optional[InferenceParameters] = None

class CategorySamplerParams(BaseModel):
    values: List[Any]

class UniformSamplerParams(BaseModel):
    low: float
    high: float

class BernoulliSamplerParams(BaseModel):
    p: float

class SamplerColumnConfig(BaseModel):
    name: str = "sampler"
    column_type: str = "sampler"
    sampler_type: SamplerType
    params: Union[CategorySamplerParams, UniformSamplerParams, BernoulliSamplerParams, Dict[str, Any]]

class ExpressionColumnConfig(BaseModel):
    name: str
    column_type: str = "expression"
    expr: str
    dtype: str = "float" # or 'bool', 'int', 'str'

class LLMTextColumnConfig(BaseModel):
    name: str
    column_type: str = "llm_text"
    model_alias: str
    system_prompt: str = ""
    prompt: str

class LLMStructuredColumnConfig(BaseModel):
    name: str
    column_type: str = "llm_structured"
    model_alias: str
    system_prompt: str = ""
    prompt: str
    output_format: Dict[str, Any] # This will accept the JSON schema of a Pydantic model

class Score(BaseModel):
    name: str
    description: str
    options: Dict[str, str]

class LLMJudgeColumnConfig(BaseModel):
    name: str 
    column_type: str = "llm_judge"
    model_alias: str
    system_prompt: str = ""
    prompt: str
    scores: List[Score]

# Union type for any column config
ColumnConfig = Union[
    SamplerColumnConfig, 
    ExpressionColumnConfig, 
    LLMTextColumnConfig, 
    LLMStructuredColumnConfig,
    LLMJudgeColumnConfig
]

class DataDesignerConfig(BaseModel):
    columns: List[ColumnConfig]
