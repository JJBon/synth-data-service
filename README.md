# NVIDIA NeMo Data Designer Setup

This project provides a Docker Compose setup for NVIDIA NeMo Data Designer service with an MCP tool for LLM-guided synthetic data generation.

## Prerequisites

- Docker and Docker Compose installed
- NVIDIA Docker runtime (nvidia-docker2)
- NVIDIA GPU with appropriate drivers
- NGC API key from NVIDIA

## Setup

1. **Configure NGC credentials:**
   ```bash
   docker login nvcr.io
   Username: $oauthtoken
   Password: <your-ngc-api-key>
   ```

2. **Create environment file:**
   ```bash
   cp .env.example .env
   # Edit .env and add your NGC API key
   ```

3. **Start the service:**
   ```bash
   docker-compose up -d
   ```

4. **Check service status:**
   ```bash
   docker-compose ps
   docker-compose logs -f nemo-data-designer
   ```

## MCP Tool Configuration

The MCP server allows LLMs to interact with NeMo Data Designer for synthetic data generation.

### Install MCP Server

**On WSL/Linux:**
```bash
chmod +x setup-mcp.sh
./setup-mcp.sh
```

**Or manually:**
```bash
cd mcp-server
npm install
```

### Configure in Kiro

Add to `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "nemo-data-designer": {
      "command": "node",
      "args": ["./mcp-server/index.js"],
      "env": {
        "NEMO_DATA_DESIGNER_URL": "http://localhost:8080"
      },
      "disabled": false,
      "autoApprove": []
    }
  }
}
```

## API Endpoints

- Health: `http://localhost:8080/health`
- Jobs: `http://localhost:8080/v1/jobs`
- Job Status: `http://localhost:8080/v1/jobs/{job_id}`

## Usage

Once configured, you can use the MCP tools in Kiro to:
- Create synthetic data generation jobs
- Monitor job status
- Retrieve generated data
- List available jobs
