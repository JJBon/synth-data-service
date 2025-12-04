#!/bin/bash

echo "Setting up NeMo Data Designer MCP Server..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Node.js is not installed. Installing..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs
fi

echo "Node version: $(node --version)"
echo "NPM version: $(npm --version)"

# Install MCP server dependencies
cd mcp-server
echo "Installing MCP server dependencies..."
npm install

echo ""
echo "✓ MCP server setup complete!"
echo ""
echo "To configure in Kiro:"
echo "1. The MCP configuration is already in .kiro/settings/mcp.json"
echo "2. Restart Kiro or reconnect the MCP server from the MCP panel"
echo ""
echo "Test the API:"
echo "curl http://localhost:8080/health"
