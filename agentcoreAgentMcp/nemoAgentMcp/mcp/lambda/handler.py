import json
from typing import Any, Dict


def lambda_handler(event, context):
    """
    Generic Lambda handler for Bedrock AgentCore Gateway placeholder tool.

    Expected input:
        event: {
            # optional tool arguments
            "param_0": val0,
            "param_1": val1,
            ...
        }

    Context should contain:
        context.client_context.custom["bedrockAgentCoreToolName"]
        → e.g. "LambdaTarget___placeholder_tool"
    """
    try:
        extended_name = context.client_context.custom.get("bedrockAgentCoreToolName")
        tool_name = None

        # handle agentcore gateway tool naming convention
        # https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/gateway-tool-naming.html
        if extended_name and "___" in extended_name:
            tool_name = extended_name.split("___", 1)[1]

        if not tool_name:
            return _response(400, {"error": "Missing tool name"})

        if tool_name != "placeholder_tool":
            return _response(400, {"error": f"Unknown tool '{tool_name}'"})

        result = placeholder_tool(event)
        return _response(200, {"result": result})

    except Exception as e:
        return _response(500, {"system_error": str(e)})


def _response(status_code: int, body: Dict[str, Any]):
    """Consistent JSON response wrapper."""
    return {"statusCode": status_code, "body": json.dumps(body)}


import os
import logging
import json
import re
import time
from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP, Context

# High-level SDK imports
try:
    from nemo_microservices.data_designer.essentials import (
        DataDesignerConfigBuilder,
        SamplerColumnConfig,
        SamplerType,
        CategorySamplerParams,
        UniformSamplerParams,
        UUIDSamplerParams,
        DatetimeSamplerParams,
        PersonSamplerParams,
        GaussianSamplerParams,
        LLMTextColumnConfig,
        ModelConfig,
        InferenceParameters,
        NeMoDataDesignerClient,
        ColumnInequalityConstraint,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("WARNING: NeMo SDK not found. Server will fail on tool calls.")

# Initialize FastMCP
mcp = FastMCP("0.0.0.0", stateless_http=True)

# Persistence configuration
STATE_FILE_PREFIX = "/tmp/nemo_mcp_state"

def _get_state_file(session_id: str) -> str:
    """Get state file path for session."""
    # Sanitize session_id to be safe for filenames
    safe_sid = "".join([c for c in session_id if c.isalnum() or c in ('-', '_')])
    if not safe_sid:
        safe_sid = "default"
    return f"{STATE_FILE_PREFIX}_{safe_sid}.json"


def _get_s3_bucket():
    # Hardcode for debugging
    return "bedrock-agentcore-codebuild-sources-668102661106-us-east-1"
    # return os.environ.get("S3_STATE_BUCKET")

def _get_state_key(session_id: str) -> str:
    # Use simple key structure
    safe_sid = "".join([c for c in session_id if c.isalnum() or c in ('-', '_')])
    if not safe_sid: safe_sid = "default"
    return f"mcp-state/{safe_sid}.json"

def _load_state(session_id: str = "default") -> Dict[str, Any]:
    """Load state from S3 or disk."""
    bucket = _get_s3_bucket()
    if bucket:
        try:
            import boto3
            s3 = boto3.client("s3")
            key = _get_state_key(session_id)
            print(f"DEBUG: Loading state from S3://{bucket}/{key}")
            obj = s3.get_object(Bucket=bucket, Key=key)
            data = json.loads(obj["Body"].read().decode("utf-8"))
            return data
        except Exception as e:
            # S3 miss or error - treat as empty session
            print(f"DEBUG: S3 load failed (new session?): {e}")
            return {"columns": [], "model_configs": [], "constraints": []}

    state_file = _get_state_file(session_id)
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Failed to load state: {e}")
    return {"columns": [], "model_configs": [], "constraints": []}

def _save_state(state: Dict[str, Any], session_id: str = "default"):
    """Save state to S3 or disk."""
    bucket = _get_s3_bucket()
    if bucket:
        try:
            import boto3
            s3 = boto3.client("s3")
            key = _get_state_key(session_id)
            s3.put_object(
                Bucket=bucket, 
                Key=key, 
                Body=json.dumps(state),
                ContentType="application/json"
            )
            print(f"DEBUG: Saved state to S3://{bucket}/{key}")
            return
        except Exception as e:
            print(f"DEBUG: Failed to save to S3: {e}")
            # Fallback to local
            
    state_file = _get_state_file(session_id)
    try:
        with open(state_file, 'w') as f:
            json.dump(state, f)
    except Exception as e:
        logging.error(f"Failed to save state: {e}")

def _validate_column_name(name: str) -> Optional[dict]:
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        return {"error": f"Invalid column name '{name}'. Use snake_case."}
    return None

def get_client():
    if SDK_AVAILABLE:
        base_url = os.environ.get("NEMO_BASE_URL", "http://aa744d0367ac64916bb1ca142fb92ead-41fcd1ae0f388842.elb.us-east-1.amazonaws.com:8000")
        return NeMoDataDesignerClient(base_url=base_url)
    return None

def rebuild_builder_from_state(session_id: str = "default") -> Any:
    """Reconstruct DataDesignerConfigBuilder from saved JSON state.
    
    CRITICAL: Must extract and pass ModelConfigs to constructor to avoid
    'Model configurations are required!' error in strict environments.
    """
    state = _load_state(session_id)
    
    # 1. Reconstruct Model Configs FIRST
    model_configs = []
    for m_data in state.get("model_configs", []):
        try:
            # Handle potential nested 'inference_parameters' dict vs object
            if "inference_parameters" in m_data and isinstance(m_data["inference_parameters"], dict):
                 m_data["inference_parameters"] = InferenceParameters(**m_data["inference_parameters"])
            model = ModelConfig(**m_data)
            model_configs.append(model)
        except Exception as e:
            logging.error(f"Failed to reconstruct model {m_data}: {e}")

    # 2. Initialize Builder with models
    # If no models found, this might prompt error if can_run_locally is false,
    # but that's expected behavior (user needs to add model first).
    # However, to be safe during column addition (if we ever need builder there), we pass empty list.
    try:
        builder = DataDesignerConfigBuilder(model_configs=model_configs)
    except Exception as e:
        # If it fails (e.g. empty list and strict check), try empty init as last resort 
        # or propagate error if it's the specific ConfigurationError
        logging.warning(f"Failed to init builder with models directly: {e}. Trying default init.")
        builder = DataDesignerConfigBuilder()
        # If that also fails, we let it crash or return None? 
        # But we are likely inside a tool execution that expects it.
        # We will add models manually if init succeeded without them (e.g. using defaults).
        for m in model_configs:
            builder.add_model_config(m)

    # 3. Re-add columns
    for c_data in state.get("columns", []):
        try:
            # Detect type and reconstruct params
            s_type = c_data.get("sampler_type")
            if s_type:
                # It's a SamplerColumnConfig
                # Need to reconstruct params object based on type
                params_data = c_data.get("params", {})
                
                # Cleanup: Remove 'sampler_type' from params if present (it's a discriminator field in output, but not valid input for init)
                if "sampler_type" in params_data:
                    del params_data["sampler_type"]

                params = None
                
                if s_type == SamplerType.CATEGORY:
                    params = CategorySamplerParams(**params_data)
                elif s_type == SamplerType.UNIFORM:
                    params = UniformSamplerParams(**params_data)
                elif s_type == SamplerType.UUID:
                    params = UUIDSamplerParams(**params_data)
                elif s_type == SamplerType.DATETIME:
                    params = DatetimeSamplerParams(**params_data)
                elif s_type == SamplerType.PERSON:
                    params = PersonSamplerParams(**params_data)
                elif s_type == SamplerType.GAUSSIAN:
                    params = GaussianSamplerParams(**params_data)
                
                if params:
                    c_data["params"] = params
                    col = SamplerColumnConfig(**c_data)
                    builder.add_column(col)
            elif "model_alias" in c_data:
                # LLMTextColumnConfig
                col = LLMTextColumnConfig(**c_data)
                builder.add_column(col)
                
        except Exception as e:
            logging.error(f"Failed to reconstruct column {c_data}: {e}")
            
    # Constraints can be added similarly if needed
    for constraint_data in state.get("constraints", []):
        try:
            # constraint_data might be simple dict: {target, op, rhs}
            if "operator" in constraint_data:
                 c = ColumnInequalityConstraint(
                     target_column=constraint_data["target_column"],
                     operator=constraint_data["operator"],
                     rhs=constraint_data["rhs_column"]
                 )
                 builder.add_constraint(c)
        except Exception as e:
            logging.error(f"Failed to reconstruct constraint: {e}")

    return builder

# --- MCP Tools ---


def init_config(ctx: Context = None) -> dict:
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    print(f"DEBUG: init_config session_id='{session_id}' ctx={ctx}")
    logging.info(f"init_config called for session: {session_id}")
    _save_state({"columns": [], "model_configs": [], "constraints": []}, session_id)
    return {"status": "initialized", "message": "Configuration reset.", "sdk_available": SDK_AVAILABLE}


def add_uuid_column(name: str, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    print(f"DEBUG: add_uuid_column session_id='{session_id}' name='{name}'")
    state = _load_state(session_id)
    # Create object to validate/get default values
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.UUID,
        params=UUIDSamplerParams(prefix="ID-", short_form=True, uppercase=True)
    )
    # Store as dict
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "uuid"}


def add_category_column(name: str, values: List[Union[str, int, float]], ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.CATEGORY,
        params=CategorySamplerParams(values=values)
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "category"}


def add_float_column(name: str, low: float, high: float, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.UNIFORM,
        params=UniformSamplerParams(low=low, high=high)
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "uniform"}


def add_int_column(name: str, low: int, high: int, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.UNIFORM,
        params=UniformSamplerParams(low=float(low), high=float(high)),
        convert_to="int"
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "integer"}


def add_datetime_column(name: str, start: str, end: str, unit: str = "s", ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.DATETIME,
        params=DatetimeSamplerParams(start=start, end=end, unit=unit)
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "datetime"}


def add_person_column(name: str, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.PERSON,
        params=PersonSamplerParams(age_range=[18, 70])
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "person"}


def add_gaussian_column(name: str, mean: float, stddev: float, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = SamplerColumnConfig(
        name=name,
        sampler_type=SamplerType.GAUSSIAN,
        params=GaussianSamplerParams(mean=mean, stddev=stddev)
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "gaussian"}


def add_llm_text_column(name: str, model_alias: str, prompt: str, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}

    if val_err := _validate_column_name(name):
        return val_err

    # Check for circular dependency in prompt
    if f"{{{{ {name} }}}}" in prompt:
         return {"error": f"Invalid Prompt: Circular dependency detected. You cannot reference the column '{name}' inside its own prompt."}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    col = LLMTextColumnConfig(
        name=name,
        model_alias=model_alias,
        prompt=prompt
    )
    state["columns"].append(col.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "column": name, "type": "llm_text", "model_alias": model_alias}


def add_model_config(alias: str = "text-gen-model", model: str = "bedrock-claude-haiku", provider: str = "litellm", temperature: float = 0.7, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    model_config = ModelConfig(
        alias=alias,
        model=model,
        provider=provider,
        inference_parameters=InferenceParameters(temperature=temperature)
    )
    state["model_configs"].append(model_config.model_dump(mode='json'))
    _save_state(state, session_id)
    return {"status": "added", "model_alias": alias}


def add_column_constraint(target_column: str, operator: str, rhs_column: str, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    op_map = {"<": "lt", "<=": "le", ">": "gt", ">=": "ge", "lt": "lt", "le": "le", "gt": "gt", "ge": "ge"}
    api_op = op_map.get(operator)
    if api_op is None:
        return {"error": f"Invalid operator: {operator}. Use: lt, le, gt, ge, <, <=, >, >="}
    
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    # Store simple rep
    constraint = {
        "target_column": target_column,
        "operator": api_op,
        "rhs_column": rhs_column
    }
    state["constraints"].append(constraint)
    _save_state(state, session_id)
    return {"status": "added", "constraint": f"{target_column} {operator} {rhs_column}"}


def get_config_summary(ctx: Context = None) -> dict:
    session_id = ctx.session_id if ctx and ctx.session_id else "default"
    state = _load_state(session_id)
    
    bucket = "bedrock-agentcore-codebuild-sources-668102661106-us-east-1" # Hardcoded for debug
    
    return {
        "num_columns": len(state.get("columns", [])),
        "num_models": len(state.get("model_configs", [])),
        "sdk_available": SDK_AVAILABLE,
        "debug_info": {
            "session_id": session_id,
            "state_source": "s3" if bucket else "local",
            "bucket_used": bucket,
            "columns_found": [c['name'] for c in state.get("columns", [])]
        }
    }


def create_job(job_name: str, num_records: int = 100, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    # Reconstruct builder from state
    try:
        session_id = ctx.session_id if ctx and ctx.session_id else "default"
        builder = rebuild_builder_from_state(session_id)
    except Exception as e:
        return {"status": "error", "message": f"Failed to rebuild config: {str(e)}"}

    # client = get_client() # Unused for manual submission

    try:
        # BYPASS SDK VALIDATION: Manual serialization to fix 'extra forbidden' fields
        config_dict = builder.build().model_dump(mode='json', exclude_none=True)

        # Removed manual None stripping loop as exclude_none=True handles it
        
        # Cleanup: Remove 'sampler_type' from params and 'column_type' from column itself
        for col in config_dict.get("columns", []):
            if "column_type" in col:
                del col["column_type"]
                
            if "params" in col and isinstance(col["params"], dict):
                if "sampler_type" in col["params"]:
                    del col["params"]["sampler_type"]

        # Construct payload manually matching Backend API
        # Verified structure from SDK source:
        # job = self._resource.jobs.create(name=name, project=project, spec=DataDesignerJobConfigParam(num_records=num_records, config=config))
        payload = {
            "name": job_name,
            "project": "nemo-data-designer",
            "spec": {
                "num_records": num_records,
                "config": config_dict
            }
        }
        
        import httpx
        base_url = os.environ.get("NEMO_BASE_URL", "http://aa744d0367ac64916bb1ca142fb92ead-41fcd1ae0f388842.elb.us-east-1.amazonaws.com:8000")
        url = f"{base_url}/v1/data-designer/jobs"
        
        # Using sync client since tool is sync
        with httpx.Client(timeout=30.0) as http_client:
            logging.info(f"Submitting job manually to {url}")
            # Ensure headers are correct if needed, but json=... usually handles Content-Type
            response = http_client.post(url, json=payload)
            logging.info(f"Response: {response}")
            
            if response.status_code >= 400:
                logging.error(f"API Error: {response.text}")
                return {
                    "status": "error", 
                    "message": f"API Error {response.status_code}: {response.text}"
                }
                
            data = response.json()
            job_id = data.get("id")
            if not job_id:
                 return {"status": "error", "message": f"No job ID in response: {data}"}
            
            return {
                "status": "submitted",
                "job_id": job_id,
                "message": f"Job {job_id} submitted."
            }
    except Exception as e:
        import traceback
        logging.error(f"Job creation failed: {e}")
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()[:500]}


def get_job_status(job_id: str) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    try:
        import httpx
        base_url = os.environ.get("NEMO_BASE_URL", "http://aa744d0367ac64916bb1ca142fb92ead-41fcd1ae0f388842.elb.us-east-1.amazonaws.com:8000")
        with httpx.Client(timeout=10.0) as h:
            res = h.get(f"{base_url}/v1/data-designer/jobs/{job_id}")
            res.raise_for_status()
            data = res.json()
        return {"job_id": job_id, "status": data.get("status", "unknown"), "message": data.get("status")}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def finalize_submission(job_id: str, session_id: str = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    # For now, just simplistic download
    base_url = os.environ.get("NEMO_BASE_URL", "http://aa744d0367ac64916bb1ca142fb92ead-41fcd1ae0f388842.elb.us-east-1.amazonaws.com:8000")
    try:
        download_url = f"{base_url}/v1/data-designer/jobs/{job_id}/results/dataset/download"
        import httpx
        import pandas as pd
        import io
        
        with httpx.Client() as h:
             r = h.get(download_url)
             r.raise_for_status()
             
             # Try JSONL
             
             # Handle tar.gz response
             import tarfile
             
             try:
                 with tarfile.open(fileobj=io.BytesIO(r.content), mode='r:gz') as tar:
                     # Find the first jsonl, csv, or parquet file
                     for member in tar.getmembers():
                         if member.name.endswith(('.jsonl', '.csv', '.parquet')):
                             f = tar.extractfile(member)
                             if f:
                                 if member.name.endswith('.jsonl'):
                                     df = pd.read_json(f, lines=True)
                                 elif member.name.endswith('.csv'):
                                     df = pd.read_csv(f)
                                 elif member.name.endswith('.parquet'):
                                     df = pd.read_parquet(f)
                                 break
                     else:
                         raise ValueError("No .jsonl, .csv, or .parquet file found in tar archive")
             except tarfile.ReadError:
                 # Fallback if not tar (e.g. plain jsonl)
                 df = pd.read_json(io.BytesIO(r.content), lines=True)
                 
        output_path = "/tmp/data-designer-output"
        os.makedirs(output_path, exist_ok=True)
        csv_path = f"{output_path}/{job_id}.csv"
        df.to_csv(csv_path, index=False)
        
        # S3 Upload
        s3_uri = None
        bucket = _get_s3_bucket()
        if bucket:
             try:
                 import boto3
                 s3 = boto3.client("s3")
                 key = f"job-results/{job_id}.csv"
                 s3.upload_file(csv_path, bucket, key)
                 s3_uri = f"s3://{bucket}/{key}"
                 print(f"DEBUG: Uploaded CSV to {s3_uri}")
             except Exception as e:
                 print(f"DEBUG: Failed to upload CSV to S3: {e}")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "local_files": {"csv": csv_path},
            "s3_uri": s3_uri,
            "preview": str(df.head(3).to_dict())
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def preview_data(num_records: int = 5, ctx: Context = None) -> dict:
    if not SDK_AVAILABLE: return {"error": "NeMo SDK not available"}
    
    try:
        session_id = ctx.session_id if ctx and ctx.session_id else "default"
        builder = rebuild_builder_from_state(session_id)
        client = get_client()
        builder.validate()
        preview = client.preview(builder, num_records=num_records)
        
        if hasattr(preview, 'dataset') and preview.dataset is not None:
            data_str = str(preview.dataset.head(3).to_dict())
        else:
            data_str = str(preview)[:2000]
        
        return {"status": "success", "data": data_str}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def download_results(job_id: str) -> dict:
    output_path = "/tmp/data-designer-output"
    csv_path = f"{output_path}/{job_id}.csv"
    if os.path.exists(csv_path):
        return {"status": "success", "local_files": {"csv": csv_path}}
    return {"status": "error", "message": "File not found"}


def import_results(job_id: str, session_id: str = None) -> dict:
    return finalize_submission(job_id, session_id)