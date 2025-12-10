# Load environment variables from .env
-include .env
export

# Paths
NEMO_COMPOSE_FILE = nemo-microservices-quickstart_v25.11/docker-compose.yaml
LOCAL_COMPOSE_FILE = docker-compose.yml
INFRA_DIR = nemo-infrastructure
GITOPS_DIR = nemo-gitops
ECR_REGISTRY = $(AWS_ACCOUNT_ID).dkr.ecr.$(AWS_REGION).amazonaws.com

.PHONY: all
all: build

# ============================================================================
# LOCAL DEVELOPMENT (Docker Compose)
# ============================================================================

.PHONY: build
build:
	@echo "Building NeMo services..."
	docker compose -f $(NEMO_COMPOSE_FILE) build
	@echo "Building Local services (MCP, Agent, LiteLLM)..."
	docker compose -f $(LOCAL_COMPOSE_FILE) build

.PHONY: up
up: up-nemo up-local

.PHONY: ngc-login
ngc-login:
	@echo "Logging into NGC registry..."
	@echo $(NGC_API_KEY) | docker login nvcr.io -u '$$oauthtoken' --password-stdin

.PHONY: up-nemo
up-nemo: ngc-login
	@echo "Starting NeMo services..."
	docker compose -f $(NEMO_COMPOSE_FILE) --profile data-designer up -d
	@echo "Waiting for NeMo network to be established..."
	sleep 5

.PHONY: up-local
up-local:
	@echo "Starting Local services..."
	docker compose -f $(LOCAL_COMPOSE_FILE) up -d

.PHONY: down
down:
	@echo "Stopping Local services..."
	docker compose -f $(LOCAL_COMPOSE_FILE) down
	@echo "Stopping NeMo services..."
	docker compose -f $(NEMO_COMPOSE_FILE) down

.PHONY: logs
logs:
	docker compose -f $(LOCAL_COMPOSE_FILE) logs -f

.PHONY: clean
clean:
	docker compose -f $(LOCAL_COMPOSE_FILE) down -v
	docker compose -f $(NEMO_COMPOSE_FILE) down -v

# ============================================================================
# INFRASTRUCTURE (Terraform)
# ============================================================================

.PHONY: infra-init
infra-init:
	cd $(INFRA_DIR) && terraform init

.PHONY: infra-plan
infra-plan:
	cd $(INFRA_DIR) && terraform plan

.PHONY: infra-apply
infra-apply:
	cd $(INFRA_DIR) && terraform apply -auto-approve

.PHONY: infra-destroy
infra-destroy:
	@echo "⚠️  Destroying all Terraform-managed infrastructure..."
	@echo "This will delete: EKS cluster, VPC, ECR repositories, etc."
	@echo "Press Ctrl+C to cancel..."
	@sleep 5
	cd $(INFRA_DIR) && terraform destroy -auto-approve

.PHONY: infra-output
infra-output:
	cd $(INFRA_DIR) && terraform output

# ============================================================================
# EKS DEPLOYMENT
# ============================================================================

.PHONY: eks-configure
eks-configure:
	@echo "Configuring kubectl for EKS cluster..."
	aws eks update-kubeconfig --region $(AWS_REGION) --name synth-data-eks

.PHONY: eks-secrets
eks-secrets:
	@echo "Creating Kubernetes secrets..."
	$(eval LITELLM_KEY_VAL := $(if $(LITELLM_KEY),$(LITELLM_KEY),sk-$(shell openssl rand -hex 16)))
	@echo "Using LITELLM_KEY: $(LITELLM_KEY_VAL)"
	kubectl create secret generic app-secrets \
		--from-literal=NIM_API_KEY=$(NIM_API_KEY) \
		--from-literal=LITELLM_KEY=$(LITELLM_KEY_VAL) \
		--from-literal=LLM_API_KEY=$(LITELLM_KEY_VAL) \
		--from-literal=AWS_ACCESS_KEY_ID=$(AWS_ACCESS_KEY_ID) \
		--from-literal=AWS_SECRET_ACCESS_KEY=$(AWS_SECRET_ACCESS_KEY) \
		--from-literal=AWS_REGION_NAME=us-east-1 \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic litellm-secrets \
		--from-literal=DATABASE_URL=postgresql://litellm:litellm@postgres:5432/litellmdb \
		--from-literal=LITELLM_MASTER_KEY=$(LITELLM_KEY_VAL) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret docker-registry ngc-registry \
		--docker-server=nvcr.io \
		--docker-username='$$oauthtoken' \
		--docker-password=$(NGC_API_KEY) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret docker-registry nvcrimagepullsecret \
		--docker-server=nvcr.io \
		--docker-username='$$oauthtoken' \
		--docker-password=$(NGC_API_KEY) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic ngc-api \
		--from-literal=NGC_API_KEY=$(NGC_API_KEY) \
		--dry-run=client -o yaml | kubectl apply -f -
	kubectl create secret generic nemo-db-secrets \
		--from-literal=DATABASE_PASSWORD=nmp \
		--dry-run=client -o yaml | kubectl apply -f -
	@echo "✅ All secrets created with LITELLM_KEY: $(LITELLM_KEY_VAL)"

.PHONY: eks-storage
eks-storage:
	@echo "Setting gp2 as default StorageClass..."
	kubectl patch storageclass gp2 -p '{"metadata": {"annotations":{"storageclass.kubernetes.io/is-default-class":"true"}}}'

.PHONY: eks-efs-sc
eks-efs-sc:
	@echo "Creating EFS StorageClass for RWX storage..."
	$(eval EFS_ID := $(shell cd $(INFRA_DIR) && terraform output -raw efs_file_system_id 2>/dev/null))
	@echo "apiVersion: storage.k8s.io/v1\nkind: StorageClass\nmetadata:\n  name: efs-sc\nprovisioner: efs.csi.aws.com\nparameters:\n  provisioningMode: efs-ap\n  fileSystemId: $(EFS_ID)\n  directoryPerms: \"700\"\nreclaimPolicy: Delete\nvolumeBindingMode: Immediate" | kubectl apply -f -
	@echo "✅ EFS StorageClass 'efs-sc' created with EFS ID: $(EFS_ID)"


.PHONY: eks-deploy
eks-deploy: eks-secrets eks-storage
	@echo "Deploying applications to EKS..."
	kubectl apply -k $(GITOPS_DIR)/apps/base/litellm/
	kubectl apply -k $(GITOPS_DIR)/apps/base/agents/
	kubectl apply -k $(GITOPS_DIR)/apps/base/nemo/

.PHONY: eks-status
eks-status:
	@echo "=== Pod Status ==="
	kubectl get pods
	@echo ""
	@echo "=== Services ==="
	kubectl get svc
	@echo ""
	@echo "=== PVCs ==="
	kubectl get pvc

.PHONY: eks-logs
eks-logs:
	@echo "Choose a service: make eks-logs-SVC (where SVC is litellm, langgraph, mcp, streamlit, data-designer)"

.PHONY: eks-logs-litellm
eks-logs-litellm:
	kubectl logs -l app=litellm --tail=50 -f

.PHONY: eks-logs-langgraph
eks-logs-langgraph:
	kubectl logs -l app=langgraph-server --tail=50 -f

.PHONY: eks-logs-mcp
eks-logs-mcp:
	kubectl logs -l app=mcp-server-sdk --tail=50 -f

.PHONY: eks-logs-streamlit
eks-logs-streamlit:
	kubectl logs -l app=streamlit-ui --tail=50 -f

.PHONY: eks-logs-data-designer
eks-logs-data-designer:
	kubectl logs -l app=data-designer --tail=50 -f

.PHONY: eks-port-forward
eks-port-forward:
	@echo "Port forwarding Streamlit UI to localhost:8501..."
	kubectl port-forward svc/streamlit-ui 8501:8501

# ============================================================================
# EKS CLEANUP
# ============================================================================

.PHONY: eks-clean-nemo
eks-clean-nemo:
	@echo "Removing NeMo deployments..."
	kubectl delete deployment nmp-core datastore entity-store openbao data-designer --ignore-not-found
	kubectl delete service nmp-core datastore entity-store openbao data-designer --ignore-not-found
	kubectl delete configmap nemo-config --ignore-not-found

.PHONY: eks-clean-helm
eks-clean-helm:
	@echo "Removing Helm releases..."
	helm uninstall nemo-platform --ignore-not-found || true
	kubectl delete pvc --all --ignore-not-found

.PHONY: eks-clean-all
eks-clean-all: eks-clean-nemo eks-clean-helm
	@echo "Removing all EKS resources..."
	kubectl delete -k $(GITOPS_DIR)/apps/base/agents/ --ignore-not-found
	kubectl delete -k $(GITOPS_DIR)/apps/base/litellm/ --ignore-not-found
	kubectl delete secret app-secrets litellm-secrets ngc-registry ngc-api nemo-db-secrets --ignore-not-found

# ============================================================================
# DOCKER BUILD & PUSH (for EKS)
# ============================================================================

.PHONY: ecr-login
ecr-login:
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)

.PHONY: docker-build-eks
docker-build-eks:
	@echo "Building images for EKS..."
	docker build -t $(ECR_REGISTRY)/mcp-server-sdk:latest ./mcp_server_py
	docker build -t $(ECR_REGISTRY)/streamlit-ui:latest ./streamlit_app
	docker build -t $(ECR_REGISTRY)/langgraph-server:latest -f ./langgraph/Dockerfile.server ./langgraph

.PHONY: docker-push-eks
docker-push-eks: ecr-login docker-build-eks
	@echo "Pushing images to ECR..."
	docker push $(ECR_REGISTRY)/mcp-server-sdk:latest
	docker push $(ECR_REGISTRY)/streamlit-ui:latest
	docker push $(ECR_REGISTRY)/langgraph-server:latest

# ============================================================================
# TESTING
# ============================================================================

.PHONY: test
test:
	pytest tests/

.PHONY: test-unit
test-unit:
	pytest tests/test_client_mock.py tests/test_verify*.py

.PHONY: test-integration
test-integration:
	pytest tests/test_agent_scenario.py tests/test_*integration*.py

.PHONY: test-all
test-all: test

# ============================================================================
# HELP
# ============================================================================

.PHONY: help
help:
	@echo "Synth Data Service - Available Commands"
	@echo ""
	@echo "Local Development:"
	@echo "  make up           - Start all local services (NeMo + agents)"
	@echo "  make down         - Stop all local services"
	@echo "  make logs         - View local service logs"
	@echo "  make clean        - Stop and remove volumes"
	@echo ""
	@echo "Infrastructure:"
	@echo "  make infra-init   - Initialize Terraform"
	@echo "  make infra-plan   - Plan infrastructure changes"
	@echo "  make infra-apply  - Apply infrastructure (create EKS, ECR, etc.)"
	@echo "  make infra-destroy - Destroy all infrastructure ⚠️"
	@echo ""
	@echo "EKS Deployment:"
	@echo "  make eks-configure - Configure kubectl for EKS"
	@echo "  make eks-secrets   - Create Kubernetes secrets"
	@echo "  make eks-deploy    - Deploy all applications to EKS"
	@echo "  make eks-status    - Show pod/service/pvc status"
	@echo "  make eks-port-forward - Forward Streamlit to localhost:8501"
	@echo ""
	@echo "EKS Cleanup:"
	@echo "  make eks-clean-nemo - Remove NeMo deployments"
	@echo "  make eks-clean-all  - Remove all EKS resources"
	@echo ""
	@echo "Docker (for EKS):"
	@echo "  make ecr-login     - Login to ECR"
	@echo "  make docker-build-eks - Build images for EKS"
	@echo "  make docker-push-eks  - Build and push to ECR"
	@echo ""
	@echo "Testing:"
	@echo "  make test          - Run all tests"
	@echo "  make test-unit     - Run unit tests only"
	@echo "  make test-integration - Run integration tests"
