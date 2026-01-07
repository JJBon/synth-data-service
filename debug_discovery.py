
import boto3
import json

def get_resources():
    session = boto3.Session(region_name='us-east-1')
    ec2 = session.client('ec2')
    iam = session.client('iam')
    ecr = session.client('ecr')
    
    results = {}
    
    # 1. Get VPC
    vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['false']}])
    if not vpcs['Vpcs']:
        print("No non-default VPC found, using default?")
        vpcs = ec2.describe_vpcs(Filters=[{'Name': 'isDefault', 'Values': ['true']}])
    
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    results['vpcId'] = vpc_id
    print(f"VPC: {vpc_id}")

    # 2. Get Public Subnets
    # We look for explicitly tagged subnets first, matching Terraform data source
    subnets = ec2.describe_subnets(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'tag:type', 'Values': ['public']}
    ])
    
    subnet_ids = [s['SubnetId'] for s in subnets['Subnets']]
    results['subnetIds'] = subnet_ids
    print(f"Public Subnets: {subnet_ids}")
    
    # 3. Get Security Group
    sgs = ec2.describe_security_groups(Filters=[
        {'Name': 'vpc-id', 'Values': [vpc_id]},
        {'Name': 'group-name', 'Values': ['agentcore-mcp-sg']}
    ])
    
    if sgs['SecurityGroups']:
        results['securityGroupId'] = sgs['SecurityGroups'][0]['GroupId']
        print(f"Security Group: {results['securityGroupId']}")
    else:
        print("ERROR: agentcore-mcp-sg not found")

    # 4. Get Role ARN
    try:
        role = iam.get_role(RoleName='agentcore-gateway-role')
        results['roleArn'] = role['Role']['Arn']
        print(f"Role ARN: {results['roleArn']}")
    except Exception as e:
        print(f"ERROR getting role: {e}")

    # 5. Get ECR URI
    try:
        repos = ecr.describe_repositories(RepositoryNames=['mcp-server-agentcore'])
        repo_uri = repos['Repositories'][0]['RepositoryUri']
        results['containerUri'] = f"{repo_uri}:latest"
        print(f"Container URI: {results['containerUri']}")
    except Exception as e:
         print(f"ERROR getting ECR: {e}")
         
    return results

if __name__ == "__main__":
    data = get_resources()
    with open("debug_config.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Saved to debug_config.json")
