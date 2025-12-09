import os
import json
import logging
import time
import httpx
import io
import tarfile
import pandas as pd
from typing import Dict, Any, List, Optional
from .models import SubmitJobRequest, JobResponse, ModelConfig, ColumnConfig

logger = logging.getLogger(__name__)

class NemoDataDesignerClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.environ.get("NEMO_DATA_DESIGNER_URL", "http://localhost:8080")
        self.client = httpx.Client(timeout=30.0)

    def get_job(self, job_id: str) -> Dict[str, Any]:
        """Fetch job details."""
        try:
            resp = self.client.get(f"{self.base_url}/v1/data-designer/jobs/{job_id}")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            msg = f"Failed to get job {job_id}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                msg += f" | Body: {e.response.text}"
            raise RuntimeError(msg)

    def download_dataset(self, job_id: str) -> List[Dict[str, Any]]:
        """Download and parse dataset (supports Parquet inside tar.gz or JSONL)."""
        try:
            download_endpoint = f"/v1/data-designer/jobs/{job_id}/results/dataset/download"
            res_resp = self.client.get(f"{self.base_url}{download_endpoint}")
            res_resp.raise_for_status()
            
            # Attempt to handle as tar.gz containing parquet (default NeMo format)
            try:
                with tarfile.open(fileobj=io.BytesIO(res_resp.content), mode="r:gz") as tar:
                    all_dfs = []
                    for member in tar.getmembers():
                        if member.isfile() and member.name.endswith(".parquet"):
                            f = tar.extractfile(member)
                            if f:
                                df = pd.read_parquet(f)
                                all_dfs.append(df)
                    
                    if all_dfs:
                        full_df = pd.concat(all_dfs, ignore_index=True)
                        # Replace NaN with safe values or leave as is (JSON standard uses null)
                        # orient='records' handles NaN as null in JSON
                        return full_df.to_dict(orient="records")
            except (tarfile.ReadError, Exception) as e:
                # Not a tar file or parquet error, fall back to text/jsonl
                logger.debug(f"Response not a valid tar/parquet ({e}), trying JSONL text.")

            # Fallback to Text/JSONL
            records = []
            for line in res_resp.text.strip().split('\n'):
                 if line.strip():
                    try:
                        records.append(json.loads(line))
                    except:
                        pass
            return records
        except httpx.HTTPError as e:
            msg = f"Failed to download dataset for {job_id}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                msg += f" | Body: {e.response.text}"
            raise RuntimeError(msg)

    def create_job(self, request: SubmitJobRequest) -> str:
        """
        Submit a job and return its ID immediately (non-blocking).
        """
        def to_dict(obj):
            """Convert Pydantic model or dict to dict, excluding None values."""
            if hasattr(obj, 'model_dump'):
                return obj.model_dump(exclude_none=True)
            elif isinstance(obj, dict):
                # Filter out None values from dict
                return {k: v for k, v in obj.items() if v is not None}
            return obj
        
        try:
            # 1. Construct Payload
            payload = {
                "name": request.job_name,
                "type": "generation",
                "spec": {
                    "num_records": request.num_samples,
                    "config": {
                        "model_configs": [to_dict(m) for m in request.model_configs],
                        "columns": [to_dict(c) for c in request.column_configs],
                    }
                }
            }
            if request.constraints:
                payload["spec"]["config"]["constraints"] = [to_dict(c) for c in request.constraints]

            # Debug: Log the payload
            logger.debug(f"Payload: {json.dumps(payload, indent=2)}")
            print(f"DEBUG PAYLOAD:\n{json.dumps(payload, indent=2)}")

            # 2. Submit Job
            logger.info(f"Submitting job '{request.job_name}' to {self.base_url}")
            response = self.client.post(f"{self.base_url}/v1/data-designer/jobs", json=payload)
            try:
                response.raise_for_status()
            except httpx.HTTPError as e:
                msg = f"NeMo API Error: {e}"
                if hasattr(e, 'response') and e.response is not None:
                    msg += f" | Body: {e.response.text}"
                logger.error(f"HTTP Error interacting with NeMo API: {e}")
                raise RuntimeError(msg)

            job_data = response.json()
            job_id = job_data.get("id")
            
            if not job_id:
                 raise Exception(f"No job_id returned. Response: {job_data}")
            
            logger.info(f"Job submitted successfully. Job ID: {job_id}")
            return job_id

        except Exception as e:
            logger.exception("Unexpected error in create_job")
            raise e

    def submit_job(self, request: SubmitJobRequest) -> JobResponse:
        """
        Submit a synthetic data generation job and wait for completion.
        """
        try:
            job_id = self.create_job(request)

            # 3. Poll for Completion
            max_retries = 900 # 15 minutes for safety with 70b models 
            status = "pending"
            for _ in range(max_retries):
                time.sleep(1)
                state = self.get_job(job_id)
                status = state.get("status", "unknown").lower()
                
                if status in ["completed", "success", "succeeded"]:
                    break
                if status in ["failed", "error"]:
                    raise Exception(f"Job failed: {state.get('message', 'Unknown error')}")
            
            if status not in ["completed", "success", "succeeded"]:
                 raise Exception(f"Job timed out or did not complete. Status: {status}")

            logger.info(f"Job {job_id} completed. Fetching results...")

            # 4. Get Result Data
            records = self.download_dataset(job_id)
            
            # 5. Return Structured Response
            return JobResponse(
                job_id=job_id,
                download_url=f"{self.base_url}/v1/data-designer/jobs/{job_id}/results/dataset/download",
                data=records[:50] # Preview first 50
            )

        except Exception as e:
            logger.exception("Unexpected error in submit_job")
            raise e
    def cancel_job(self, job_id: str) -> Dict[str, Any]:
        """Cancel a running job."""
        try:
            resp = self.client.post(f"{self.base_url}/v1/data-designer/jobs/{job_id}/cancel")
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            msg = f"Failed to cancel job {job_id}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                msg += f" | Body: {e.response.text}"
            raise RuntimeError(msg)

    def get_job_status(self, job_id: str) -> str:
        """Get the status of a job."""
        try:
            resp = self.client.get(f"{self.base_url}/v1/data-designer/jobs/{job_id}/status")
            resp.raise_for_status()
            # Assuming payload has { "status": "..." } or similar
            # Based on spec: PlatformJobStatusResponse
            return resp.json().get("status", "unknown")
        except httpx.HTTPError as e:
            # Fallback to get_job if status endpoint fails (backward compatibility)
            try:
                return self.get_job(job_id).get("status", "unknown")
            except:
                raise RuntimeError(f"Failed to get status for {job_id}: {e}")

    def get_job_logs(self, job_id: str) -> List[str]:
        """Get the logs of a job."""
        try:
            resp = self.client.get(f"{self.base_url}/v1/data-designer/jobs/{job_id}/logs")
            resp.raise_for_status()
            # Spec: PlatformJobLogPage -> data: List[PlatformJobLog] -> message
            data = resp.json().get("data", [])
            return [log.get("message", "") for log in data]
        except httpx.HTTPError as e:
            msg = f"Failed to get logs for {job_id}: {e}"
            if hasattr(e, 'response') and e.response is not None:
                msg += f" | Body: {e.response.text}"
            raise RuntimeError(msg)

    def preview_job(self, request: SubmitJobRequest) -> List[Dict[str, Any]]:
        """Generate a preview for the job configuration."""
        try:
            # Payload similar to submit but different wrapper
            payload = {
                "spec": {
                    "num_records": request.num_samples,
                    "config": {
                        "model_configs": [m.model_dump() for m in request.model_configs],
                        "columns": [c.model_dump() for c in request.column_configs],
                    }
                }
                # Might need constraints/seed if preview supports them
            }
            if request.constraints:
                payload["spec"]["config"]["constraints"] = [c.model_dump() for c in request.constraints]

            resp = self.client.post(f"{self.base_url}/v1/data-designer/preview", json=payload)
            resp.raise_for_status()
            
            # Response is JSONL
            records = []
            for line in resp.text.strip().split('\n'):
                if line.strip():
                     try:
                         # Spec: PreviewMessage -> data keys? Or just list of dicts?
                         # Usually preview returns rows.
                         # Spec: PreviewMessage
                         val = json.loads(line)
                         records.append(val)
                     except:
                         pass
            return records
        except httpx.HTTPError as e:
            msg = f"Failed to preview job: {e}"
            if hasattr(e, 'response') and e.response is not None:
                 msg += f" | Body: {e.response.text}"
            raise RuntimeError(msg)
