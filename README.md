# NVIDIA NeMo Data Designer MCP Server

This project provides a Python-based MCP (Model Context Protocol) server for the NVIDIA NeMo Data Designer service, allowing LLMs to guide synthetic data generation.

## Prerequisites

- Python 3.10+
- Docker and Docker Compose (for the NeMo Data Designer service)
- NVIDIA GPU (recommended for NeMo Data Designer)
- NGC API Key

## Setup

1.  **Start the NeMo Data Designer Service:**
    ```bash
    docker-compose up -d
    ```
    Ensure you have configured your `.env` file with your `NGC_API_KEY`.

2.  **Install the MCP Server:**
    ```bash
    cd mcp_server_py
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## Usage

### Running the MCP Server
You can run the MCP server directly:
```bash
# In mcp_server_py/
python server.py
```

### Integration with Kiro (or other MCP clients)
Add the following to your MCP settings (e.g., `~/.kiro/settings/mcp.json`):

```json
{
  "mcpServers": {
    "nemo-data-designer": {
      "command": "python3",
      "args": ["/path/to/synth-data-service/mcp_server_py/server.py"],
      "env": {
        "NEMO_DATA_DESIGNER_URL": "http://localhost:8080"
      }
    }
  }
}
```

## Development

### Running Tests
```bash
pytest
```

## Project Structure

- `mcp_server_py/`: Python MCP server implementation.
- `tests/`: Pytest tests.
- `docker-compose.yml`: Docker Compose setup for NeMo Data Designer.
