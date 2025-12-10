# Pending: NeMo Data Designer EKS Deployment

**Last Updated:** 2025-12-10 11:12 EST

## Current State - WORKING ✅

### ✅ All Components Running
| Component | Status |
|-----------|--------|
| PostgreSQL | ✅ Running |
| LiteLLM | ✅ Running (Bedrock Claude Haiku) |
| LangGraph Server | ✅ Running |
| Streamlit UI | ✅ Running |
| MCP Server SDK | ✅ Running |
| NeMo Data Designer (Helm) | ✅ Running |
| NeMo Core API | ✅ Running |
| NeMo Core Controller | ✅ Running |
| NeMo Data Store | ✅ Running |
| NeMo JobsDB | ✅ Running |
| NeMo PostgreSQL | ✅ Running |

### ✅ Job Execution Working
- [x] **Fetch and Display Results**:
    - [x] Create `import_results` MCP tool (`server_sdk.py`) to fetch/stage CSV files.
    - [x] Switch UI to use In-Memory DuckDB for fast, stateless data visualization.
    - [x] Implement file watcher in Streamlit to auto-import new CSVs from shared volume.
    - [x] Fix file locking and concurrency issues via architecture change (Artifacts vs Memory).
- [ ] **Data Export**:
    - [x] Add CSV/Parquet download buttons to Streamlit UI.
- Results available via NeMo API download endpoints

### Access URLs (via port-forward)
```bash
# Streamlit UI
kubectl port-forward svc/streamlit-ui 8501:8501
# Access: http://localhost:8501

# NeMo Data Designer API
kubectl port-forward svc/nemo-data-designer 8000:8000
# Access: http://localhost:8000

# LiteLLM
kubectl port-forward svc/litellm 4000:4000
# Access: http://localhost:4000
```

## GitOps (Flux) Integration

### Flux HelmRelease
- Location: `nemo-gitops/apps/base/nemo/helmrelease.yaml`
- Manages NeMo Data Designer via Helm
- References `nmp/nemo-microservices-helm-chart:25.11.*`

### Automated Secrets
```bash
# From .env file, run:
make eks-secrets
# Auto-generates LITELLM_KEY if not set
# Creates: app-secrets, litellm-secrets, ngc-registry, nvcrimagepullsecret, ngc-api, nemo-db-secrets
```

## Makefile Commands

### Infrastructure
```bash
make infra-init   # Initialize Terraform
make infra-apply  # Create EKS + EFS infrastructure
make infra-destroy  # Destroy all infrastructure
```

### EKS Deployment
```bash
make eks-secrets   # Create all secrets (auto-generates LITELLM_KEY)
make eks-storage   # Set gp2 as default StorageClass
make eks-efs-sc    # Create EFS StorageClass from Terraform output
make eks-deploy    # Deploy all applications
make eks-status    # Check pod/service/pvc status
```

### ECR Image Management
```bash
make ecr-login      # Login to ECR
make ecr-build      # Build images locally
make ecr-push       # Push images to ECR
```

## Environment Variables Required

```bash
# In .env file:
NGC_API_KEY=...           # NGC catalog access
NIM_API_KEY=...           # NVIDIA API access
AWS_ACCESS_KEY_ID=...     # AWS credentials
AWS_SECRET_ACCESS_KEY=... # AWS credentials
AWS_REGION=us-east-1      # AWS region

# LITELLM_KEY is auto-generated if not set
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (:8501)                      │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  LangGraph Server (:8003)                    │
│                     (Agent/Reasoner)                         │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                  MCP Server SDK (:8002)                      │
│              (NeMo Tools: preview, create_job)               │
└─────────────────────────┬───────────────────────────────────┘
                          │
         ┌────────────────┴────────────────┐
         ▼                                 ▼
┌──────────────────┐            ┌──────────────────┐
│  NeMo Data       │            │    LiteLLM       │
│  Designer        │────────────│    (:4000)       │
│  (:8000)         │            │ (Bedrock Claude) │
└────────┬─────────┘            └──────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────┐
│                    NeMo Core Services                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐ │
│  │Core API  │ │Controller│ │Data Store│ │ EFS Storage (RWX)│ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```
