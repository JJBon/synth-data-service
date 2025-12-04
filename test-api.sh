#!/bin/bash

echo "Testing NeMo Data Designer API..."
echo ""

# Test health endpoint
echo "1. Health Check:"
curl -s http://localhost:8080/health | jq .
echo ""

# Create a test job
echo "2. Creating a test job..."
JOB_RESPONSE=$(curl -s -X POST http://localhost:8080/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-qa-job",
    "task_type": "question_answering",
    "num_samples": 50,
    "config": {
      "domain": "machine_learning",
      "difficulty": "medium"
    }
  }')

echo "$JOB_RESPONSE" | jq .
JOB_ID=$(echo "$JOB_RESPONSE" | jq -r .job_id)
echo ""

# Check job status
echo "3. Checking job status (Job ID: $JOB_ID)..."
sleep 2
curl -s http://localhost:8080/v1/jobs/$JOB_ID | jq .
echo ""

# List all jobs
echo "4. Listing all jobs..."
curl -s http://localhost:8080/v1/jobs | jq .
echo ""

echo "Waiting for job to complete (10 seconds)..."
sleep 10

# Get job results
echo "5. Getting job results..."
curl -s http://localhost:8080/v1/jobs/$JOB_ID/results | jq .
echo ""

echo "✓ API test complete!"
