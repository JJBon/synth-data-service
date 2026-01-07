
import boto3

candidates = ['bedrock-agent', 'bedrock-agentcore-control', 'bedrock']
for name in candidates:
    print(f"\n--- {name} ---")
    try:
        client = boto3.client(name, region_name='us-east-1')
        ops = client.meta.method_to_api_mapping
        # Filter for create operations to be concise
        creates = [op for op in ops if 'create' in op]
        for c in creates:
            print(f"- {c}")
        if 'create_agent_runtime' in ops:
            print(f"!!! FOUND create_agent_runtime in {name} !!!")
    except Exception as e:
        print(f"Error: {e}")
