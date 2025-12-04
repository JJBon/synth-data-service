# NeMo Data Designer Usage Guide

## Quick Start

### 1. Start the Service

**Windows:**
```cmd
start.bat
```

**Linux/Mac:**
```bash
chmod +x start.sh
./start.sh
```

### 2. Install MCP Server Dependencies

```bash
cd mcp-server
npm install
```

### 3. Verify Service is Running

```bash
curl http://localhost:8080/health
```

## Using the MCP Tools

Once configured, you can interact with NeMo Data Designer through Kiro using natural language. The MCP server provides these tools:

### Available Tools

1. **guide_job_creation** - Get AI-guided recommendations for your data generation needs
2. **create_synthetic_data_job** - Create a new data generation job
3. **get_job_status** - Check the status of a running job
4. **list_jobs** - View all your jobs
5. **get_job_results** - Retrieve generated data from completed jobs
6. **cancel_job** - Stop a running job

### Example Conversations with Kiro

**Example 1: Generate Q&A Data**
```
You: I need to generate 500 question-answer pairs about machine learning

Kiro will:
1. Use guide_job_creation to understand your needs
2. Recommend task_type: "question_answering"
3. Suggest configuration parameters
4. Create the job using create_synthetic_data_job
5. Monitor progress with get_job_status
```

**Example 2: Text Classification Data**
```
You: Create synthetic data for a sentiment classifier with 3 classes

Kiro will:
1. Guide you through the setup
2. Recommend task_type: "classification"
3. Configure num_classes: 3
4. Create and monitor the job
```

**Example 3: Check Job Progress**
```
You: What's the status of my jobs?

Kiro will:
1. Use list_jobs to show all jobs
2. Use get_job_status for specific jobs
3. Retrieve results when complete
```

## Job Configuration Examples

### Question Answering
```json
{
  "job_name": "ml-qa-dataset",
  "task_type": "question_answering",
  "num_samples": 500,
  "config": {
    "domain": "machine_learning",
    "difficulty": "medium",
    "answer_length": "medium"
  }
}
```

### Text Summarization
```json
{
  "job_name": "news-summaries",
  "task_type": "summarization",
  "num_samples": 200,
  "config": {
    "source_length": "long",
    "summary_length": "short",
    "style": "abstractive"
  }
}
```

### Classification
```json
{
  "job_name": "sentiment-data",
  "task_type": "classification",
  "num_samples": 1000,
  "config": {
    "num_classes": 3,
    "class_labels": ["positive", "negative", "neutral"],
    "balance": "balanced"
  }
}
```

## Troubleshooting

### Service Won't Start
- Verify Docker is running: `docker ps`
- Check NVIDIA Docker runtime: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`
- View logs: `docker-compose logs -f`

### MCP Server Not Connecting
- Ensure Node.js is installed: `node --version`
- Check MCP server logs in Kiro's MCP panel
- Verify service is accessible: `curl http://localhost:8080/health`

### Authentication Issues
- Login to NGC: `docker login nvcr.io`
- Username: `$oauthtoken`
- Password: Your NGC API key

## API Reference

For direct API access (without MCP):

### Create Job
```bash
curl -X POST http://localhost:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-job",
    "task_type": "text_generation",
    "num_samples": 100
  }'
```

### Get Job Status
```bash
curl http://localhost:8080/v1/jobs/{job_id}
```

### List Jobs
```bash
curl http://localhost:8080/v1/jobs?limit=10
```

### Get Results
```bash
curl http://localhost:8080/v1/jobs/{job_id}/results
```
