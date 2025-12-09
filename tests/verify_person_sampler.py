
import logging
import time
import sys
import os
sys.path.append(os.getcwd())
from mcp_server_py.client import NemoDataDesignerClient
from mcp_server_py.models import SubmitJobRequest, SamplerColumnConfig, SamplerType, PersonSamplerParams

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def verify_person_sampler():
    client = NemoDataDesignerClient()
    
    # Define a person column with parameters matching documentation EXACTLY
    person_col = SamplerColumnConfig(
        name="customer",
        sampler_type=SamplerType.PERSON,
        params=PersonSamplerParams(
            locale="en_US",
            sex="Female", # Docs say "Male" or "Female"
            city="New York",
            age_range=[25, 35],
            with_synthetic_personas=True
        )
    )
    
    req = SubmitJobRequest(
        job_name=f"verify_person_sampler_{int(time.time())}",
        model_configs=[], # No LLM needed for sampler-only job
        column_configs=[person_col],
        num_samples=5
    )
    
    try:
        print("Submitting job with PersonSamplerParams...")
        job_id = client.create_job(req)
        print(f"Job submitted successfully. ID: {job_id}")
        
        # Poll for completion
        for _ in range(60):
            status = client.get_job_status(job_id)
            print(f"Status: {status}")
            if status.lower() in ["completed", "success", "succeeded"]:
                print("Job completed!")
                data = client.download_dataset(job_id)
                print("Data preview:", data)
                return True
            if status.lower() in ["failed", "error"]:
                print("Job failed.")
                logs = client.get_job_logs(job_id)
                print("Logs:\n", "\n".join(logs))
                return False
            time.sleep(2)
            
    except Exception as e:
        print(f"Submission failed: {e}")
        return False

if __name__ == "__main__":
    verify_person_sampler()
