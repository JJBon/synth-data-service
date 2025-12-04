#!/bin/bash

echo "=========================================="
echo "NeMo Data Designer MCP Workflow Test"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}This script demonstrates the workflow that the MCP server will automate${NC}"
echo ""

# Step 1: Guide job creation
echo -e "${GREEN}Step 1: Getting guidance for job creation${NC}"
echo "User asks: 'I need to generate question-answer pairs about Python'"
echo ""
echo "MCP tool: guide_job_creation"
echo "Response would recommend:"
cat << 'EOF'
{
  "recommendations": [
    {
      "task_type": "question_answering",
      "description": "Generate question-answer pairs for training or evaluation",
      "suggested_config": {
        "domain": "Python programming",
        "difficulty": "medium",
        "answer_length": "medium"
      }
    }
  ]
}
EOF
echo ""
sleep 2

# Step 2: Create job
echo -e "${GREEN}Step 2: Creating synthetic data job${NC}"
echo "MCP tool: create_synthetic_data_job"
echo ""

JOB_RESPONSE=$(curl -s -X POST http://localhost:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "python-qa-dataset",
    "task_type": "question_answering",
    "num_samples": 100,
    "config": {
      "domain": "python_programming",
      "difficulty": "medium",
      "answer_length": "medium"
    }
  }')

echo "$JOB_RESPONSE" | jq .
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r .job_id)
echo ""
sleep 2

# Step 3: Monitor job
echo -e "${GREEN}Step 3: Monitoring job progress${NC}"
echo "MCP tool: get_job_status"
echo ""

for i in {1..3}; do
  echo "Check #$i:"
  curl -s http://localhost:8080/v1/jobs/$JOB_ID | jq '{job_id, name, status, progress}'
  echo ""
  sleep 3
done

# Step 4: List all jobs
echo -e "${GREEN}Step 4: Listing all jobs${NC}"
echo "MCP tool: list_jobs"
echo ""
curl -s http://localhost:8080/v1/jobs | jq '.jobs[] | {job_id, name, status, progress}'
echo ""
sleep 2

# Step 5: Get results
echo -e "${GREEN}Step 5: Retrieving generated data${NC}"
echo "MCP tool: get_job_results"
echo ""
echo "Waiting for job to complete..."
sleep 5

RESULTS=$(curl -s http://localhost:8080/v1/jobs/$JOB_ID/results)
echo "$RESULTS" | jq '.results[0:3]'  # Show first 3 samples
echo ""
echo "Total samples generated: $(echo "$RESULTS" | jq '.num_samples')"
echo ""

echo "=========================================="
echo -e "${GREEN}✓ Workflow Complete!${NC}"
echo "=========================================="
echo ""
echo "This is what happens automatically when you chat with Kiro:"
echo "1. You describe what data you need"
echo "2. MCP server guides you through configuration"
echo "3. Job is created and monitored"
echo "4. Results are retrieved when ready"
echo ""
echo "All through natural language conversation!"
