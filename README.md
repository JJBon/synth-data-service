# Synthetic Data Service

An autonomous agentic workflow for synthetic data generation using NVIDIA NeMo Data Designer, powered by a custom Model Context Protocol (MCP) server.

## Quick Start (Local)

### 1. Configure Environment
```bash
cp .env.example .env
# Edit .env with your keys (LITELLM_KEY, NIM_API_KEY, etc.)
```

### 2. Run Stack
```bash
make up
```

**Access:**
- Streamlit UI: http://localhost:8501
- LiteLLM Proxy: http://localhost:4000

```bash
make down  # Stop services
```

---

## Deployment Guide (AWS EKS)

### Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform, Docker, kubectl installed

### Step 1: Provision Infrastructure
```bash
make infra-init
make infra-apply
```
Note the output `ecr_repository_urls` for the next step.

### Step 2: Build & Push Images
```bash
# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
make ecr-push
```

### Step 3: Configure kubectl
```bash
make eks-configure
```

### Step 4: Create Secrets
```bash
make eks-secrets
```

### Step 5: Deploy Applications
```bash
make eks-deploy
```

### Step 6: Verify
```bash
make eks-status
```

**Access Streamlit UI:**
```bash
kubectl get svc streamlit-ui -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
# Opens at port 8501
```

---

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed component descriptions.

```
User → Streamlit UI → LangGraph Agent → MCP Server → NeMo Data Designer
                              ↓
                         LiteLLM Proxy → AWS Bedrock / OpenAI / NIM
```

**Components:**
| Component | Description |
|-----------|-------------|
| **NeMo Data Designer** | NVIDIA synthetic data generation microservice |
| **MCP Server** | Exposes NeMo capabilities as tools for agents |
| **LangGraph Agent** | Autonomous reasoner that designs datasets |
| **LiteLLM** | Universal LLM API proxy |
| **Streamlit** | User interface |

---

## Makefile Commands

| Command | Description |
|---------|-------------|
| `make up` | Start local Docker stack |
| `make down` | Stop local stack |
| `make test` | Run all tests |
| `make infra-apply` | Provision AWS infrastructure |
| `make eks-deploy` | Deploy to EKS |
| `make eks-status` | Check pod/service status |
