
import boto3
import json

client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
# ID from previous run output
runtime_id = "manual_debug_210514-d8qm2v8drN" 

try:
    resp = client.get_agent_runtime(agentRuntimeId=runtime_id)
    print("Full Status Response:")
    print(json.dumps(resp, indent=2, default=str))
except Exception as e:
    print(f"Error: {e}")
