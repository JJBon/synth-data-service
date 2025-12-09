# Load environment variables from .env
-include .env
export

# Paths
NEMO_COMPOSE_FILE = nemo-microservices-quickstart_v25.11/docker-compose.yaml
LOCAL_COMPOSE_FILE = docker-compose.yml
INFRA_DIR = nemo-infrastructure

.PHONY: all
all: build

# --- Build & Push ---
.PHONY: build
build:
	@echo "Building NeMo services..."
	docker compose -f $(NEMO_COMPOSE_FILE) build
	@echo "Building Local services (MCP, Agent, LiteLLM)..."
	docker compose -f $(LOCAL_COMPOSE_FILE) build

.PHONY: push
push:
	docker compose -f $(NEMO_COMPOSE_FILE) push
	docker compose -f $(LOCAL_COMPOSE_FILE) push

# --- Runtime Management ---
.PHONY: up
up: up-nemo up-local

.PHONY: up-nemo
up-nemo:
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

# --- Infrastructure (Terraform) ---
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
	cd $(INFRA_DIR) && terraform destroy -auto-approve

# --- Testing ---
.PHONY: test
test:
	pytest tests/

.PHONY: test-unit
test-unit:
	# Run tests that don't require external connections or complex graph execution
	pytest tests/test_client_mock.py tests/test_verify*.py

.PHONY: test-integration
test-integration:
	# Run scenario and integration tests
	pytest tests/test_agent_scenario.py tests/test_*integration*.py

.PHONY: test-all
test-all: test
