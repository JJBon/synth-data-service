
FROM python:3.11-slim

WORKDIR /app

# Install fastmcp and uvicorn (required for streamable-http)
RUN pip install --no-cache-dir fastmcp uvicorn

# Copy mock server code
COPY mock_server.py /app/mock_server.py

# Expose port
EXPOSE 8000

# Environment variables for AgentCore
ENV MCP_TRANSPORT=streamable-http
ENV PYTHONUNBUFFERED=1

CMD ["python", "/app/mock_server.py"]
