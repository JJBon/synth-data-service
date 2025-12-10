# Pending: NeMo Data Designer EKS Deployment

**Last Updated:** 2025-12-09 23:04 EST

## Current State

### ✅ Working Components
- **PostgreSQL** (`postgres-56c5fc85bd`) - Running, has `nmp` user and databases (`entitystore`, `datastore`, `jobs`)
- **LiteLLM** (`litellm-9ddbc68b6`) - Running at `litellm:4000`, configured with Bedrock Claude Haiku
- **LangGraph Server** (`langgraph-server-787cbd6f84`) - Running
- **Streamlit UI** (`streamlit-ui-55f6c46b5b`) - Running
- **MCP Server SDK** (`mcp-server-sdk-6f5569d87d`) - Running with `nemo-microservices` SDK, `NEMO_BASE_URL=http://data-designer:8000`

### ⏳ NeMo Platform Deployment (Partially Working)

#### Manual Deployment Approach (Closer to Working)
Files: `nemo-gitops/apps/base/nemo/deployment.yaml`, `nemo-gitops/apps/base/nemo/core-stack.yaml`

**What worked:**
- `data-designer` - Running, preview works perfectly
- `datastore` - Running
- `nmp-core` - Running (needed `--quickstart` arg, not `infra --quickstart`)
- `openbao` - Running (needed `bao server` command, not `server`)
- `entity-store` - Can run but needs postgres connection

**Issue:** Job creation from `data-designer` → `nmp-core` returned `APIConnectionError: Connection error`. The `nemo-config` ConfigMap has `jobs_url: http://nmp-core:8000` but connection fails.

#### Helm Chart Approach (Stalled)
**Commands run:**
```bash
helm repo add nmp https://helm.ngc.nvidia.com/nvidia/nemo-microservices --username='$oauthtoken' --password=$NGC_API_KEY
kubectl create secret generic ngc-api --from-literal=NGC_API_KEY=$NGC_API_KEY
kubectl create secret docker-registry nvcrimagepullsecret --docker-server=nvcr.io --docker-username='$oauthtoken' --docker-password=$NGC_API_KEY
kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'
```

**Issues:**
1. **ReadWriteMany (RWX) storage required** - Data-store and job storage need RWX, but EBS (`gp2`) only supports RWO
2. **Need AWS EFS** with EFS CSI driver for shared storage
3. Helm install timed out / stalled with pending PVCs

### 🔄 What Was Proven Working
- **Preview data generation works end-to-end:**
  - Agent adds columns → MCP calls SDK → data-designer generates with LiteLLM/Bedrock → returns preview data
  - LLM text columns generated successfully with Claude Haiku
  - 10 successful LLM requests with 0 failures

## Next Steps (Choose One)

### Option 1: Fix Manual Deployment (Recommended for Quick Win)
The `APIConnectionError` between `data-designer` and `nmp-core` needs investigation:
1. Check if `nmp-core` health endpoint works: `kubectl exec -it <pod> -- curl http://nmp-core:8000/health`
2. May need to configure `nmp-core` with proper database connection
3. Check `nmp-core` logs for startup errors

### Option 2: Set Up AWS EFS for Helm Chart
```bash
# Add EFS CSI driver
helm repo add aws-efs-csi-driver https://kubernetes-sigs.github.io/aws-efs-csi-driver/
helm install aws-efs-csi-driver aws-efs-csi-driver/aws-efs-csi-driver --namespace kube-system

# Create EFS file system in Terraform or AWS console
# Create StorageClass for EFS with ReadWriteMany
```

### Option 3: Use Preview-Only Workflow
The `preview_data` function works perfectly. If job execution is not critical, the current setup can generate sample data.

## Files Modified/Created

| File | Purpose |
|------|---------|
| `nemo-gitops/apps/base/nemo/deployment.yaml` | Data-designer + full nemo-config |
| `nemo-gitops/apps/base/nemo/core-stack.yaml` | nmp-core, datastore, entity-store, openbao |
| `nemo-gitops/helm/nemo-values.yaml` | Custom values for Helm chart (LiteLLM integration) |
| `mcp_server_py/requirements.txt` | Added `python-json-logger` for SDK |

## Environment Variables Required
```bash
# In nemo-db-secrets
DATABASE_PASSWORD=nmp

# In app-secrets
NIM_API_KEY=...
LITELLM_KEY=...
NGC_API_KEY=... (also in ngc-api secret)
```

## Cleanup Commands
```bash
# Remove helm release if needed
helm uninstall nemo-platform

# Remove manual NeMo deployments
kubectl delete deployment nmp-core datastore entity-store openbao data-designer
kubectl delete service nmp-core datastore entity-store openbao data-designer
kubectl delete configmap nemo-config

# Remove PVCs
kubectl delete pvc --all
```
