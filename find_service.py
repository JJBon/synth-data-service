
import boto3

session = boto3.Session()
services = session.get_available_services()
print("Bedrock Services found:")
for s in services:
    if 'bedrock' in s:
        print(f"- {s}")
