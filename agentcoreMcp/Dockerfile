FROM public.ecr.aws/docker/library/python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
# Ensure NeMo URL is set (fallback is already in code, but explicit is good)
# ENV NEMO_BASE_URL=... (User set it in code default)

# Expose port (FastMCP streamable-http default is 8000? or 8080?)
ENV S3_STATE_BUCKET=bedrock-agentcore-codebuild-sources-668102661106-us-east-1
EXPOSE 8000

# Run the server
CMD ["python", "my_mcp_server.py"]
