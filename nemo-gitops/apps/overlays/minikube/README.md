# Minikube Deployment Guide

This overlay allows you to run the synthetic data service on Minikube instead of AWS EKS.

## Prerequisites

- [Minikube](https://minikube.sigs.k8s.io/docs/start/) installed
- Docker installed
- kubectl installed

## Quick Start

### 1. Start Minikube

```bash
# Start with sufficient resources
minikube start --memory=8192 --cpus=4 --disk-size=50g

# Enable ingress addon (optional)
minikube addons enable ingress
```

### 2. Build Images into Minikube

```bash
# Point Docker CLI to Minikube's daemon
eval $(minikube docker-env)

# Build images
cd /path/to/synth-data-service
docker build -t mcp-server-sdk:local -f mcp_server_py/Dockerfile .
docker build -t streamlit-ui:local -f streamlit_app/Dockerfile .
docker build -t langgraph-server:local -f langgraph/Dockerfile.server .

# Verify images are built
docker images | grep local
```

### 3. Create Secrets

```bash
kubectl create secret generic app-secrets \
  --from-literal=LITELLM_KEY=sk-your-key \
  --from-literal=NIM_API_KEY=your-nim-key \
  --from-literal=AWS_ACCESS_KEY_ID=your-aws-key \
  --from-literal=AWS_SECRET_ACCESS_KEY=your-aws-secret \
  --from-literal=AWS_REGION_NAME=us-east-1

kubectl create secret generic litellm-secrets \
  --from-literal=LITELLM_MASTER_KEY=sk-your-key \
  --from-literal=DATABASE_URL=postgresql://postgres:postgres@postgres:5432/litellm
```

### 4. Deploy with Kustomize

```bash
# Deploy the Minikube overlay
kubectl apply -k nemo-gitops/apps/overlays/minikube/

# Check status
kubectl get pods
```

### 5. Access the UI

```bash
# Option A: Use minikube service command
minikube service streamlit-ui --url

# Option B: Port-forward
kubectl port-forward svc/streamlit-ui 8501:8501

# Then open: http://localhost:8501
```

## Running NeMo Data Designer

For the full pipeline, you also need NeMo Data Designer. Options:

### Option A: Docker Compose (Recommended for Dev)

Run NeMo via Docker Compose in a separate terminal:
```bash
cd nemo-microservices-quickstart_v25.11
docker compose --profile data-designer up
```

Then update MCP to point to host Docker:
```bash
# In Minikube, host.minikube.internal resolves to host machine
kubectl set env deployment/mcp-server-sdk \
  NEMO_BASE_URL=http://host.minikube.internal:8000
```

### Option B: Deploy NeMo in Minikube

Apply the NeMo Helm chart to Minikube (requires more resources).

## Differences from EKS

| Feature | EKS | Minikube |
|---------|-----|----------|
| LoadBalancer | AWS ELB | NodePort (30501) |
| Storage | EFS | Local hostPath |
| Images | ECR | Local Docker |
| Auto-scaling | Karpenter | N/A (single node) |
| S3 | AWS S3 | Disabled (local files) |

## Troubleshooting

### Images not found
```bash
# Ensure you're using Minikube's Docker daemon
eval $(minikube docker-env)
docker images | grep local
```

### Services not accessible
```bash
# Check service status
kubectl get svc
minikube service list
```

### Reset everything
```bash
kubectl delete -k nemo-gitops/apps/overlays/minikube/
minikube delete
```
