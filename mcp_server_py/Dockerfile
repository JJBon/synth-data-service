FROM python:3.11-slim

WORKDIR /

# Install system dependencies if needed
# RUN apt-get update && apt-get install -y gcc

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . mcp_server_py/

# Environment variables
ENV NEMO_DATA_DESIGNER_URL=http://nemo-data-designer:8080
ENV NEMO_BASE_URL=http://nemo-data-designer:8080

# Default to original server; use docker-compose override for SDK server
CMD ["python", "mcp_server_py/server_sdk.py"]
