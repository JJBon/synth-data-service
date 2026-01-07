
import boto3

client = boto3.client('bedrock-agentcore', region_name='us-east-1')
print("Operations:")
for op in client.meta.method_to_api_mapping:
    print(f"- {op}")
