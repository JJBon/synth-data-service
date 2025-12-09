# Synthetic Data Service (NeMo Data Designer + MCP Agent)

This project implements an autonomous agentic workflow for synthetic data generation using NVIDIA NeMo Data Designer, powered by a custom Model Context Protocol (MCP) server.

## Quick Start

The project is managed via a `Makefile`.

### 1. Configure Environment
Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
# Edit .env with your keys (LITELLM_KEY, NIM_API_KEY, etc.)
```

### 2. Run Local Environment
Start the full stack (NeMo Data Designer, LiteLLM, MCP Server, Agent, Streamlit UI):
```bash
make up
```

Access the services:
- **Streamlit UI:** http://localhost:8501
- **LiteLLM Proxy:** http://localhost:4000
- **NeMo Data Designer:** http://localhost:8080 (if port mapped)

To stop services:
```bash
make down
```

### 3. Run Tests
Execute unit and integration tests:
```bash
# Run all tests
make test

# Run only unit tests (offline)
make test-unit

# Run integration tests (requires 'make up')
make test-integration
```

## Infrastructure Deployment (AWS EKS)

This project supports GitOps deployment to AWS EKS via Terraform and FluxCD.

```bash
# Initialize and apply Terraform infrastructure
make infra-init
make infra-apply
```

For detailed deployment steps, please refer to [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md).

## Architecture

For a detailed explanation of the services and their interactions, see [ARCHITECTURE.md](ARCHITECTURE.md).

---
**Components:**
- **NeMo Data Designer:** Synthetic data generation microservice.
- **MCP Server:** Exposes NeMo capabilities as tools for agents.
- **LangGraph Agent:** Autonomous reasoner that designs datasets.
- **LiteLLM:** Universal LLM API proxy.
- **Streamlit:** User interface.
