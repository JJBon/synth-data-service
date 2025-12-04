#!/bin/bash

echo "📊 NeMo Data Designer - View Generated Data"
echo "=========================================="
echo ""

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo "⚠️  jq is not installed. Installing..."
    sudo apt-get update && sudo apt-get install -y jq
fi

# List all jobs
echo "📋 Available Jobs:"
echo ""

for file in jobs/*.json; do
    if [ -f "$file" ]; then
        job_name=$(jq -r '.name' "$file")
        job_id=$(jq -r '.job_id' "$file")
        task_type=$(jq -r '.task_type' "$file")
        num_samples=$(jq -r '.num_samples' "$file")
        status=$(jq -r '.status' "$file")
        
        echo "  📁 $job_name"
        echo "     ID: $job_id"
        echo "     Type: $task_type"
        echo "     Samples: $num_samples"
        echo "     Status: $status"
        echo "     File: $file"
        echo ""
    fi
done

echo "=========================================="
echo ""
echo "💡 To view a specific job's data:"
echo "   cat jobs/<job-id>.json | jq ."
echo ""
echo "💡 To view just the results:"
echo "   cat jobs/<job-id>.json | jq '.results'"
echo ""
echo "💡 To export results to CSV (example for Q&A):"
echo "   cat jobs/<job-id>.json | jq -r '.results[] | [.id, .question, .answer] | @csv' > output.csv"
echo ""
echo "💡 To view in this script, pass job ID as argument:"
echo "   ./view-data.sh <job-id>"
echo ""

# If job ID provided, show that job's data
if [ ! -z "$1" ]; then
    job_file="jobs/$1.json"
    if [ -f "$job_file" ]; then
        echo "=========================================="
        echo "📄 Job Details:"
        echo "=========================================="
        cat "$job_file" | jq '.'
    else
        echo "❌ Job file not found: $job_file"
    fi
fi
