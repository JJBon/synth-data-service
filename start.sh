#!/bin/bash

echo "Starting NVIDIA NeMo Data Designer..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from .env.example..."
    cp .env.example .env
    echo "Please edit .env and add your NGC API key"
    exit 1
fi

# Create necessary directories
mkdir -p data jobs

# Start Docker Compose
docker-compose up -d

echo "Waiting for service to be healthy..."
sleep 10

# Check health
curl -f http://localhost:8080/health || echo "Service not ready yet, check logs with: docker-compose logs -f"

echo ""
echo "NeMo Data Designer is starting!"
echo "Check status: docker-compose ps"
echo "View logs: docker-compose logs -f nemo-data-designer"
echo ""
echo "To configure MCP server:"
echo "1. cd mcp-server && npm install"
echo "2. Add configuration to .kiro/settings/mcp.json (see README.md)"
