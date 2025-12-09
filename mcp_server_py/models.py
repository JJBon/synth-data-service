from enum import Enum
from typing import List, Optional, Union, Dict, Any
from pydantic import BaseModel, Field

class SamplerType(str, Enum):
    CATEGORY = "category"
    UNIFORM = "uniform"
    BERNOULLI = "bernoulli"
    BINOMIAL = "binomial"
    BERNOULLI_MIXTURE = "bernoulli_mixture"
    INTEGER = "integer"
    FLOAT = "float"
    UUID = "uuid"
    DATETIME = "datetime"
    PERSON = "person"
    GAUSSIAN = "gaussian"

class InferenceParameters(BaseModel):
    temperature: float = 0.6
    top_p: float = 0.95
    max_tokens: int = 1024

class ModelConfig(BaseModel):
    alias: str
    model: str
    provider: str = "nvidiabuild"
    inference_parameters: InferenceParameters = Field(default_factory=InferenceParameters)

class CategorySamplerParams(BaseModel):
    values: List[Any]

class UniformSamplerParams(BaseModel):
    low: float
    high: float

class BernoulliSamplerParams(BaseModel):
    p: float

class BinomialSamplerParams(BaseModel):
    n: int
    p: float

class BernoulliMixtureSamplerParams(BaseModel):
    p: float
    dist_name: str
    dist_params: Dict[str, Any]

class GaussianSamplerParams(BaseModel):
    mean: float
    stddev: float

class PersonSamplerParams(BaseModel):
    locale: str = "en_US"
    sex: Optional[str] = None
    city: Optional[Union[str, List[str]]] = None
    age_range: Optional[List[int]] = None 
    with_synthetic_personas: bool = False

class IntegerSamplerParams(BaseModel):
    low: int
    high: int

class UUIDSamplerParams(BaseModel):
    pass # No params needed for standard UUID generation

class DatetimeSamplerParams(BaseModel):
    start: str
    end: str
    unit: str = "seconds" # or days, hours, etc.

class SamplerColumnConfig(BaseModel):
    name: str = "sampler"
    sampler_type: SamplerType
    params: Union[
        CategorySamplerParams, 
        UniformSamplerParams, 
        BernoulliSamplerParams, 
        IntegerSamplerParams, 
        BinomialSamplerParams,
        BernoulliMixtureSamplerParams,
        UUIDSamplerParams,
        DatetimeSamplerParams,
        PersonSamplerParams,
        GaussianSamplerParams,
        Dict[str, Any]
    ]
    drop: bool = False

class CodeLang(str, Enum):
    PYTHON = "python"
    SQL = "sql"

class CodeValidatorParams(BaseModel):
    language: CodeLang
    timeout: int = 30
    
class ScalarInequalityConstraint(BaseModel):
    target_column: str
    operator: str # <, <=, >, >=, ==, !=
    value: float

class ColumnInequalityConstraint(BaseModel):
    target_column: str
    operator: str  # 'lt', 'le', 'gt', 'ge'
    rhs: str  # The right-hand side column name

class ExpressionColumnConfig(BaseModel):
    name: str
    expr: str
    dtype: str = "float"
    drop: bool = False

class SeedConfig(BaseModel):
    # Depending on spec this might be complex, assuming generic for now or from spec
    # Spec ref says: SeedConfig -> SeedDatasetColumnConfig? No, SeedConfig in Config.
    # Looking at spec, SeedConfig is likely referencing a dataset ID or file.
    # Simplified placeholder based on standard patterns if detailed attributes needed.
    # Spec: $ref: '#/components/schemas/SeedConfig' -> (not fully expanded in quick view, assuming placeholder)
    # Actually, let's leave it as generic Dict if unsure, or empty.
    # Re-reading spec snippet... it's just referenced.
    pass

class ValidationColumnConfig(BaseModel):
    name: str
    validator: str 
    drop: bool = False

class ImageContext(BaseModel):
    url: str

class LLMTextColumnConfig(BaseModel):
    name: str
    model_alias: str
    prompt: str
    system_prompt: Optional[str] = ""
    multi_modal_context: Optional[List[ImageContext]] = None
    drop: bool = False

class LLMStructuredColumnConfig(BaseModel):
    name: str
    model_alias: str
    prompt: str
    output_format: Dict[str, Any]
    system_prompt: Optional[str] = ""
    multi_modal_context: Optional[List[ImageContext]] = None
    drop: bool = False

class Score(BaseModel):
    name: str
    description: str
    options: Dict[str, str]

class LLMJudgeColumnConfig(BaseModel):
    name: str 
    model_alias: str
    prompt: str
    scores: List[Score]
    system_prompt: Optional[str] = ""
    multi_modal_context: Optional[List[ImageContext]] = None
    drop: bool = False

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
    constraints: Optional[List[ColumnInequalityConstraint]] = None

class SubmitJobRequest(BaseModel):
    job_name: str
    model_configs: List[ModelConfig]
    column_configs: List[ColumnConfig]
    constraints: Optional[List[Union[ScalarInequalityConstraint, ColumnInequalityConstraint]]] = None
    seed_config: Optional[SeedConfig] = None
    num_samples: int = 100

class JobResponse(BaseModel):
    job_id: str
    download_url: str
    data: List[Dict[str, Any]]
