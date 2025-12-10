"""
SDK-based MCP Server for NeMo Data Designer.

This version uses the official nemo_microservices Python SDK
with the high-level DataDesignerConfigBuilder API.
"""

import os
import logging
import re
from typing import List, Dict, Any, Optional, Union
from fastmcp import FastMCP
import time

# High-level SDK imports
try:
    from nemo_microservices.data_designer.essentials import (
        DataDesignerConfigBuilder,
        SamplerColumnConfig,
        SamplerType,
        CategorySamplerParams,
        UniformSamplerParams,
        UUIDSamplerParams,  # Note: uppercase UUID
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
except ImportError as e:
    logging.warning(f"NeMo high-level SDK not available: {e}. Using stub mode.")
    SDK_AVAILABLE = False

# Initialize FastMCP
mcp = FastMCP("nemo-data-designer-sdk")

# Global state using high-level config builder
_config_builder: Optional[Any] = None
_client: Optional[Any] = None
_job_results: Dict[str, Any] = {}  # Store job_results by job_id


def _validate_column_name(name: str) -> Optional[dict]:
    """Validate column name for Jinja2 compatibility."""
    if not re.match(r"^[a-zA-Z0-9_]+$", name):
        return {
            "error": f"Invalid column name '{name}'. Use snake_case (a-z, 0-9, _) only. Spaces are not allowed."
        }
    return None


def get_client():
    """Get or create the high-level SDK client."""
    global _client
    if _client is None and SDK_AVAILABLE:
        base_url = os.environ.get("NEMO_BASE_URL", "http://localhost:8080")
        _client = NeMoDataDesignerClient(base_url=base_url)
    return _client


def get_config_builder():
    """Get or create the config builder."""
    global _config_builder
    if _config_builder is None and SDK_AVAILABLE:
        _config_builder = DataDesignerConfigBuilder()
    return _config_builder


def reset_config_builder():
    """Reset the config builder to start fresh."""
    global _config_builder
    if SDK_AVAILABLE:
        _config_builder = DataDesignerConfigBuilder()
    return _config_builder



def reset_config():
    """Reset the configuration to start fresh."""
    reset_config_builder()


# --- MCP Tools ---

@mcp.tool()
def init_config() -> dict:
    """
    Initialize a new Data Designer configuration.
    This resets any existing configuration and starts fresh.
    Call this at the beginning of each new dataset design session.
    """
    reset_config_builder()
    return {
        "status": "initialized",
        "message": "Configuration reset. Ready to add columns.",
        "sdk_available": SDK_AVAILABLE
    }


@mcp.tool()
def add_uuid_column(name: str) -> dict:
    """
    Add a UUID column that generates unique identifiers.
    Use for: 'ID', 'Transaction ID', 'User ID', 'Invoice ID'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.UUID,
            params=UUIDSamplerParams(prefix="DEMO-", short_form=True, uppercase=True)
        )
    )
    return {"status": "added", "column": name, "type": "uuid"}


@mcp.tool()
def add_category_column(name: str, values: List[Union[str, int, float]]) -> dict:
    """
    Add a column that samples from a fixed list of values.
    Use for: 'Status' (['Paid','Unpaid']), 'Currency' (['USD','EUR']).
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=values)
        )
    )
    return {"status": "added", "column": name, "type": "category", "values": values}


@mcp.tool()
def add_float_column(name: str, low: float, high: float) -> dict:
    """
    Add a column that samples floats uniformly from a range [low, high].
    Use for: 'Price', 'Amount', 'Temperature', 'Score'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.UNIFORM,
            params=UniformSamplerParams(low=low, high=high)
        )
    )
    return {"status": "added", "column": name, "type": "uniform", "range": [low, high]}


@mcp.tool()
def add_category_column(name: str, values: List[Union[str, int, float]]) -> dict:
    """
    Add a column that samples from a fixed list of values.
    Use for: 'Status' (['Paid','Unpaid']), 'Currency' (['USD','EUR']).
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.CATEGORY,
            params=CategorySamplerParams(values=values)
        )
    )
    return {"status": "added", "column": name, "type": "category", "values": values}


@mcp.tool()
def add_float_column(name: str, low: float, high: float) -> dict:
    """
    Add a column that samples floats uniformly from a range [low, high].
    Use for: 'Price', 'Amount', 'Temperature', 'Score'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.UNIFORM,
            params=UniformSamplerParams(low=low, high=high)
        )
    )
    return {"status": "added", "column": name, "type": "uniform", "range": [low, high]}


@mcp.tool()
def add_int_column(name: str, low: int, high: int) -> dict:
    """
    Add a column that samples integers uniformly from a range [low, high].
    Use for: 'Age', 'Quantity', 'Year', 'Count'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.UNIFORM,
            params=UniformSamplerParams(low=float(low), high=float(high)),
            convert_to="int"
        )
    )
    return {"status": "added", "column": name, "type": "integer", "range": [low, high]}


@mcp.tool()
def add_datetime_column(name: str, start: str, end: str, unit: str = "s") -> dict:
    """
    Add a column that samples datetimes uniformly from a range.
    Format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS'.
    Unit: 's' (second), 'm' (minute), 'h' (hour), 'D' (day).
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.DATETIME,
            params=DatetimeSamplerParams(start=start, end=end, unit=unit)
        )
    )
    return {"status": "added", "column": name, "type": "datetime", "range": [start, end]}


@mcp.tool()
def add_person_column(name: str) -> dict:
    """
    Add a column that samples realistic person data (name, address, etc).
    Use for: 'Customer Name', 'User', 'Contact', 'Employee'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.PERSON,
            params=PersonSamplerParams(age_range=[18, 70])  # Explicit params required
        )
    )
    return {"status": "added", "column": name, "type": "person"}


@mcp.tool()
def add_gaussian_column(name: str, mean: float, stddev: float) -> dict:
    """
    Add a column that samples from a Gaussian (Normal) distribution.
    Use for: 'Height', 'Weight', 'Test Scores'.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    builder.add_column(
        SamplerColumnConfig(
            name=name,
            sampler_type=SamplerType.GAUSSIAN,
            params=GaussianSamplerParams(mean=mean, stddev=stddev)
        )
    )
    return {"status": "added", "column": name, "type": "gaussian", "mean": mean, "stddev": stddev}


@mcp.tool()
def add_llm_text_column(name: str, model_alias: str, prompt: str) -> dict:
    """
    Add a column generated by an LLM using a prompt template.
    Use Jinja2 syntax to reference other columns: '{{ column_name }}'.
    IMPORTANT: You must add a model config first using add_model_config.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}

    if val_err := _validate_column_name(name):
        return val_err
    
    # Check for circular dependency in prompt
    if f"{{{{ {name} }}}}" in prompt:
         return {"error": f"Invalid Prompt: Circular dependency detected. You cannot reference the column '{name}' inside its own prompt."}
    
    builder = get_config_builder()
    builder.add_column(
        LLMTextColumnConfig(
            name=name,
            model_alias=model_alias,
            prompt=prompt
        )
    )
    return {"status": "added", "column": name, "type": "llm_text", "model_alias": model_alias}


@mcp.tool()
def add_model_config(alias: str = "text-gen-model", model: str = "bedrock-claude-haiku", provider: str = "litellm", temperature: float = 0.7) -> dict:
    """
    Add a model configuration for LLM-based columns.
    Must be called before adding LLM text columns.
    
    Available models via LiteLLM:
    - 'bedrock-claude-haiku' (recommended, fast)
    - 'gpt-4o' (OpenAI)
    - 'llama-3.1-8b-128k-local' (local vLLM)
    
    Args:
        alias: A reference name for this model (default: 'text-gen-model')
        model: The LiteLLM model name (default: 'bedrock-claude-haiku')
        provider: Model provider (default: 'litellm')
        temperature: Sampling temperature (default: 0.7)
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    model_config = ModelConfig(
        alias=alias,
        model=model,
        provider=provider,
        inference_parameters=InferenceParameters(temperature=temperature)
    )
    builder.add_model_config(model_config)
    return {"status": "added", "model_alias": alias, "model": model, "provider": provider}


@mcp.tool()
def add_column_constraint(target_column: str, operator: str, rhs_column: str) -> dict:
    """
    Add an inequality constraint between two columns.
    
    Args:
        target_column: Left-hand side column
        operator: One of 'lt' (<), 'le' (<=), 'gt' (>), 'ge' (>=)
        rhs_column: Right-hand side column
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    # Map user-friendly operators to API string values
    op_map = {
        "<": "lt",
        "<=": "le",
        ">": "gt",
        ">=": "ge",
        "lt": "lt",
        "le": "le",
        "gt": "gt",
        "ge": "ge",
    }
    api_op = op_map.get(operator)
    if api_op is None:
        return {"error": f"Invalid operator: {operator}. Use: lt, le, gt, ge, <, <=, >, >="}
    
    builder = get_config_builder()
    constraint = ColumnInequalityConstraint(
        target_column=target_column,
        operator=api_op,
        rhs=rhs_column
    )
    builder.add_constraint(constraint)
    return {"status": "added", "constraint": f"{target_column} {operator} {rhs_column}"}


@mcp.tool()
def get_config_summary() -> dict:
    """
    Get a summary of the current configuration.
    Use to review what has been configured before submitting a job.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available"}
    
    builder = get_config_builder()
    columns = builder.columns if hasattr(builder, 'columns') else []
    models = builder.model_configs if hasattr(builder, 'model_configs') else []
    
    column_names = [c.name if hasattr(c, 'name') else str(c) for c in columns]
    model_aliases = [m.alias if hasattr(m, 'alias') else str(m) for m in models]
    
    return {
        "num_columns": len(columns),
        "columns": column_names,
        "num_models": len(models),
        "models": model_aliases,
        "ready_to_submit": len(columns) > 0,
        "sdk_available": SDK_AVAILABLE
    }


@mcp.tool()
def preview_data(num_records: int = 5) -> dict:
    """
    Generate a quick preview of the data without creating a full job.
    Useful for validating your configuration before submitting.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    client = get_client()
    builder = get_config_builder()
    
    try:
        # Validate config before preview
        builder.validate()
        
        # Use high-level SDK preview
        preview = client.preview(builder, num_records=num_records)
        
        # Get preview data - handle None case
        if preview is None:
            return {"status": "error", "message": "Preview returned None"}
        
        if hasattr(preview, 'dataset') and preview.dataset is not None:
            data_str = str(preview.dataset.head(3).to_dict())
        else:
            data_str = str(preview)[:2000]
        
        return {
            "status": "success",
            "num_records": num_records,
            "data": data_str
        }
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()[:500]}


@mcp.tool()
def create_job(job_name: str, num_records: int = 100) -> dict:
    """
    Submit a synthetic data generation job.
    
    Args:
        job_name: Name label for the job
        num_records: Number of records to generate
    
    Returns:
        Job ID and status information
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    client = get_client()
    builder = get_config_builder()
    
    try:
        # Validate config before job submission
        builder.validate()
        
        # Use high-level SDK create method (non-blocking)
        job_result = client.create(builder, num_records=num_records, name=job_name)
        
        # Get actual job ID from the result
        job_info = job_result.get_job()
        job_id = job_info.id if hasattr(job_info, 'id') else str(job_info)
        
        # Store job_result for later use
        _job_results[job_id] = job_result
        
        # Return immediately - don't block
        return {
            "status": "submitted",
            "job_id": job_id,
            "num_records": num_records,
            "message": f"Job {job_id} submitted. Poll get_job_status({job_id}) until status='completed', then call finalize_job({job_id}) to save results."
        }
        
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()[:500]}


@mcp.tool()
def get_job_status(job_id: str) -> dict:
    """
    Get the status of a previously submitted job.
    Poll this until status='completed', then call finalize_job.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    try:
        import httpx
        base_url = os.environ.get("NEMO_BASE_URL", "http://localhost:8080")
        with httpx.Client(timeout=30.0) as http_client:
            response = http_client.get(f"{base_url}/v1/data-designer/jobs/{job_id}")
            response.raise_for_status()
            job_data = response.json()
        
        status = job_data.get("status", "unknown")
        result = {
            "job_id": job_id,
            "status": status,
            "name": job_data.get("name"),
            "error_details": job_data.get("error_details")
        }
        
        if status == "completed":
            result["message"] = f"Job completed! Call finalize_job('{job_id}') to save and download results."
        elif status == "error":
            result["message"] = "Job failed. Check error_details."
        else:
            result["message"] = f"Job still running (status: {status}). Poll again in 10 seconds."
        
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def finalize_submission(job_id: str, session_id: str = None) -> dict:
    """
    Finalize a completed job: load dataset, save to files, and return preview.
    Call this AFTER get_job_status returns status='completed'.
    
    Args:
        job_id: The ID of the job to finalize.
        session_id: Optional session ID to namespace the S3 upload.
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    if job_id not in _job_results:
        return {"status": "error", "message": f"Job {job_id} not found in session. Make sure you created this job in the current session."}
    
    try:
        job_result = _job_results[job_id]
        
        # Wait for completion (should already be done if get_job_status returned completed)
        job_result.wait_until_done()
        
        # Load dataset
        dataset = job_result.load_dataset()
        preview = dataset.head(5).to_dict() if hasattr(dataset, 'head') else str(dataset)[:1000]
        
        # Auto-save to volume
        output_path = "/tmp/data-designer-output"
        os.makedirs(output_path, exist_ok=True)
        
        # Save dataset as CSV and Parquet
        dataset_csv_path = f"{output_path}/{job_id}.csv"
        dataset_parquet_path = f"{output_path}/{job_id}.parquet"
        dataset.to_csv(dataset_csv_path, index=False)
        dataset.to_parquet(dataset_parquet_path, index=False)
        
        # Download artifacts
        artifacts_path = f"{output_path}/artifacts-{job_id}"
        job_result.download_artifacts(output_path=output_path, artifacts_folder_name=f"artifacts-{job_id}")
        
        # Upload to S3 if configured
        s3_bucket = os.environ.get("S3_ARTIFACTS_BUCKET")
        if s3_bucket:
             try:
                 import boto3
                 s3_client = boto3.client("s3")
                 key = f"data/{session_id}/{job_id}.csv" if session_id else f"data/{job_id}.csv"
                 logging.info(f"Uploading {dataset_csv_path} to s3://{s3_bucket}/{key}")
                 s3_client.upload_file(dataset_csv_path, s3_bucket, key)
             except Exception as e:
                 logging.error(f"S3 upload in finalize_job failed: {e}")

        # NeMo download URLs
        nemo_base_url = os.environ.get("NEMO_BASE_URL", "http://localhost:8080")
        
        return {
            "status": "completed",
            "job_id": job_id,
            "preview": preview,
            "local_files": {
                "csv": dataset_csv_path,
                "parquet": dataset_parquet_path,
                "artifacts": artifacts_path
            },
            "host_path": "./data-designer-output",
            "nemo_download_urls": {
                "dataset": f"{nemo_base_url}/v1/data-designer/jobs/{job_id}/results/dataset/download",
                "analysis": f"{nemo_base_url}/v1/data-designer/jobs/{job_id}/results/analysis/download"
            },
            "message": f"Job finalized. Files saved to {output_path}"
        }
        
    except Exception as e:
        import traceback
        return {"status": "error", "message": str(e), "traceback": traceback.format_exc()[:500]}


@mcp.tool()
def download_results(job_id: str) -> dict:
    """
    Get download links/paths for a completed job's results.
    Files are auto-saved during job creation.
    
    Returns:
    - Local file paths (for development/volume access)
    - NeMo API download URLs (for cloud integration)
    """
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    output_path = "/tmp/data-designer-output"
    dataset_csv_path = f"{output_path}/{job_id}.csv"
    dataset_parquet_path = f"{output_path}/{job_id}.parquet"
    artifacts_path = f"{output_path}/artifacts-{job_id}"
    
    # Check if files exist
    csv_exists = os.path.exists(dataset_csv_path)
    parquet_exists = os.path.exists(dataset_parquet_path)
    artifacts_exists = os.path.exists(artifacts_path)
    
    # NeMo API base URL (for cloud)
    nemo_base_url = os.environ.get("NEMO_BASE_URL", "http://localhost:8080")
    
    # Build response with both local and API download links
    result = {
        "status": "success",
        "job_id": job_id,
        "local_files": {
            "csv": dataset_csv_path if csv_exists else None,
            "parquet": dataset_parquet_path if parquet_exists else None,
            "artifacts": artifacts_path if artifacts_exists else None
        },
        "host_path": "./data-designer-output",  # Host mount path for local dev
        "nemo_download_urls": {
            "dataset": f"{nemo_base_url}/v1/data-designer/jobs/{job_id}/results/dataset/download",
            "analysis": f"{nemo_base_url}/v1/data-designer/jobs/{job_id}/results/analysis/download"
        },
        "message": f"Files saved locally and available via NeMo API"
    }
    
    if not (csv_exists or parquet_exists):
        result["warning"] = "Local files not found - use NeMo download URLs instead"
    
    return result


@mcp.tool()
def import_results(job_id: str, session_id: str = None) -> dict:
    """
    Import job results into shared database for display in UI sidebar.
    
    This tool fetches the job results (from local file or NeMo API) and 
    ensures the CSV file is present in the S3 bucket or shared volume.
    
    Args:
        job_id: The job ID to import results for
        session_id: Optional session ID to namespace the S3 upload.
    
    Returns:
        Status message confirming file availability for the UI to pick up.
    """
    import httpx
    import pandas as pd
    import io
    import time
    
    if not SDK_AVAILABLE:
        return {"error": "NeMo SDK not available", "status": "stub_mode"}
    
    output_path = "/tmp/data-designer-output"
    csv_path = f"{output_path}/{job_id}.csv"
    
    try:
        source = None
        
        # Try local file first
        if os.path.exists(csv_path):
            source = "local_file"
            logging.info(f"Checking local file: {csv_path}")
            # Touch the file to signal it's "new" for the UI watcher
            os.utime(csv_path, None)
        else:
            # Fetch from NeMo API
            nemo_base_url = os.environ.get("NEMO_BASE_URL", "http://localhost:8080")
            download_url = f"{nemo_base_url}/v1/data-designer/jobs/{job_id}/results/dataset/download"
            
            logging.info(f"Fetching results from: {download_url}")
            response = httpx.get(download_url, timeout=60)
            
            if response.status_code == 200:
                # Save raw content directly to file (bypass pandas parsing to avoid "bad lines" errors)
                source = "nemo_api"
                logging.info(f"Fetched {len(response.content)} bytes from NeMo API")
                
                # Save locally for shared access
                os.makedirs(output_path, exist_ok=True)
                with open(csv_path, "wb") as f:
                    f.write(response.content)
            else:
                return {
                    "status": "error",
                    "message": f"Failed to fetch results: HTTP {response.status_code}",
                    "download_url": download_url
                }
        
        # Upload to S3 if configured
        s3_bucket = os.environ.get("S3_ARTIFACTS_BUCKET")
        if s3_bucket:
            try:
                import boto3
                s3_client = boto3.client("s3")
                key = f"data/{session_id}/{job_id}.csv" if session_id else f"data/{job_id}.csv"
                logging.info(f"Uploading {csv_path} to s3://{s3_bucket}/{key}")
                s3_client.upload_file(csv_path, s3_bucket, key)
                return {
                    "status": "success",
                    "job_id": job_id,
                    "source": "s3",
                    "s3_uri": f"s3://{s3_bucket}/{key}",
                    "message": f"Results uploaded to s3://{s3_bucket}/{key}"
                }
            except Exception as e:
                logging.error(f"S3 upload failed: {e}")
                return {"error": f"Failed to upload to S3: {str(e)}"}

        return {
            "status": "success",
            "job_id": job_id,
            "source": source,
            "message": "Results imported (file ready for UI)"
        }
            
    except Exception as e:
        import traceback
        logging.error(f"Error importing results: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()[:500]
        }


# --- Main Entry Point ---

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    port = int(os.environ.get("MCP_PORT", "8002"))
    stateless = os.environ.get("MCP_STATELESS", "false").lower() == "true"

    # Re-initialize mcp if stateless mode is requested (required for AgentCore)
    if stateless:
        mcp = FastMCP("nemo-data-designer-sdk", host=host, port=port, stateless_http=True)
    
    if not SDK_AVAILABLE:
        logging.warning("Running in stub mode - NeMo SDK not installed or import failed")
    else:
        logging.info("NeMo SDK loaded successfully with proper type classes")

    if transport == "stdio":
        mcp.run(transport="stdio")
    elif transport == "sse":
        mcp.run(transport="sse", host=host, port=port)
    elif transport == "streamable-http":
        # AgentCore runtime expects streamable-http
        mcp.run(transport="streamable-http")
    else:
        logging.warning(f"Unknown transport {transport}, defaulting to stdio")
        mcp.run(transport="stdio")
