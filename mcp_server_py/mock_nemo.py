from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List
import uuid

app = FastAPI()

class JobPayload(BaseModel):
    name: str
    config: Dict[str, Any]
    num_samples: int
    type: str

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/v1/jobs")
def create_job(payload: JobPayload):
    print(f"Received Job Submission: {payload.name}")
    print(f"Config: {payload.config.keys()}")
    return {
        "job_id": str(uuid.uuid4()),
        "status": "pending",
        "message": "Mock job created successfully"
    }

@app.get("/v1/jobs/{job_id}")
def get_job(job_id: str):
    return {
        "job_id": job_id,
        "status": "completed",
        "progress": 1.0,
        "results": []
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
