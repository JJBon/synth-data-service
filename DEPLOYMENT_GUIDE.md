# NeMo Data Designer - Deployment Guide

This guide outlines the steps to deploy the full stack (NeMo, LiteLLM, MCP Agent, Streamlit UI) to AWS EKS using Terraform and FluxCD.

## Prerequisites
- AWS CLI configured with appropriate permissions.
- Terraform installed.
- Flux CLI installed.
- Docker installed.

## Step 1: Provision Infrastructure and ECR

Run the following command to provision the EKS cluster and ECR repositories:

```bash
make infra-init
make infra-apply
```

**IMPORTANT:** Note the output `ecr_repository_urls` containing the URLs for:
- `mcp-server-sdk`
- `streamlit-ui`
- `langgraph-server`

## Step 2: Build and Push Images

Login to ECR:
```bash
aws ecr get-login-password --region <YOUR_REGION> | docker login --username AWS --password-stdin <YOUR_ACCOUNT_ID>.dkr.ecr.<YOUR_REGION>.amazonaws.com
```

Build and push the images using the URLs from Step 1:

**MCP Server:**
```bash
docker build -t <MCP_REPO_URL>:latest -f mcp_server_py/Dockerfile .
docker push <MCP_REPO_URL>:latest
```

**Streamlit UI:**
```bash
docker build -t <STREAMLIT_REPO_URL>:latest -f streamlit_app/Dockerfile .
docker push <STREAMLIT_REPO_URL>:latest
```

**LangGraph Server:**
```bash
docker build -t <LANGGRAPH_REPO_URL>:latest -f langgraph/Dockerfile.server .
docker push <LANGGRAPH_REPO_URL>:latest
```

## Step 3: Update GitOps Manifests

Update the deployment manifests in `nemo-gitops/apps/base/agents/` with the specific ECR image URLs you just pushed.

- `deployment.yaml` (MCP Server) -> `<MCP_REPO_URL>:latest`
- `streamlit.yaml` -> `<STREAMLIT_REPO_URL>:latest`
- `langgraph.yaml` -> `<LANGGRAPH_REPO_URL>:latest`

Commit and push these changes to your git repository:
```bash
git add nemo-gitops
git commit -m "Update image references"
git push
```

## Step 4: Bootstrap FluxCD

Connect your EKS cluster to your git repository to start the deployment:

```bash
flux bootstrap github \
  --owner=<YOUR_GITHUB_USER> \
  --repository=synth-data-service \
  --branch=main \
  --path=nemo-gitops/clusters/my-cluster \
  --personal
```

## Step 5: Configure Secrets

Create the necessary secrets in the cluster for the applications to function:

```bash
kubectl create secret generic app-secrets \
  --from-literal=LITELLM_KEY=<your_key> \
  --from-literal=NIM_API_KEY=<your_key> \
  --from-literal=OPENAI_API_KEY=<your_key>
```

## Step 6: Verify Deployment

Monitor the Flux reconciliation and pod status:

```bash
flux get kustomizations --watch
kubectl get pods -A
```
