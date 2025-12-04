#!/bin/bash

echo "📦 NeMo Data Designer - Export Data"
echo "=========================================="
echo ""

if [ -z "$1" ]; then
    echo "Usage: ./export-data.sh <job-id> [format]"
    echo ""
    echo "Formats:"
    echo "  json   - Export as JSON (default)"
    echo "  csv    - Export as CSV"
    echo "  txt    - Export as plain text"
    echo ""
    echo "Example:"
    echo "  ./export-data.sh 37a76929-871c-4646-93d9-fd4a247f21d5 csv"
    echo ""
    exit 1
fi

JOB_ID=$1
FORMAT=${2:-json}
JOB_FILE="jobs/$JOB_ID.json"

if [ ! -f "$JOB_FILE" ]; then
    echo "❌ Job file not found: $JOB_FILE"
    exit 1
fi

# Get job info
JOB_NAME=$(jq -r '.name' "$JOB_FILE")
TASK_TYPE=$(jq -r '.task_type' "$JOB_FILE")
NUM_SAMPLES=$(jq -r '.num_samples' "$JOB_FILE")

echo "📋 Job: $JOB_NAME"
echo "🔧 Type: $TASK_TYPE"
echo "📊 Samples: $NUM_SAMPLES"
echo ""

# Create exports directory
mkdir -p exports

case $FORMAT in
    json)
        OUTPUT_FILE="exports/${JOB_NAME}_${JOB_ID}.json"
        jq '.results' "$JOB_FILE" > "$OUTPUT_FILE"
        echo "✅ Exported to: $OUTPUT_FILE"
        ;;
    
    csv)
        OUTPUT_FILE="exports/${JOB_NAME}_${JOB_ID}.csv"
        
        case $TASK_TYPE in
            question_answering)
                echo "id,question,answer,context" > "$OUTPUT_FILE"
                jq -r '.results[] | [.id, .question, .answer, .context] | @csv' "$JOB_FILE" >> "$OUTPUT_FILE"
                ;;
            
            classification)
                echo "id,text,label,confidence" > "$OUTPUT_FILE"
                jq -r '.results[] | [.id, .text, .label, .confidence] | @csv' "$JOB_FILE" >> "$OUTPUT_FILE"
                ;;
            
            summarization)
                echo "id,source_text,summary" > "$OUTPUT_FILE"
                jq -r '.results[] | [.id, .source_text, .summary] | @csv' "$JOB_FILE" >> "$OUTPUT_FILE"
                ;;
            
            text_generation)
                echo "id,text" > "$OUTPUT_FILE"
                jq -r '.results[] | [.id, .text] | @csv' "$JOB_FILE" >> "$OUTPUT_FILE"
                ;;
            
            *)
                echo "❌ Unknown task type: $TASK_TYPE"
                exit 1
                ;;
        esac
        
        echo "✅ Exported to: $OUTPUT_FILE"
        ;;
    
    txt)
        OUTPUT_FILE="exports/${JOB_NAME}_${JOB_ID}.txt"
        
        echo "Job: $JOB_NAME" > "$OUTPUT_FILE"
        echo "Type: $TASK_TYPE" >> "$OUTPUT_FILE"
        echo "Samples: $NUM_SAMPLES" >> "$OUTPUT_FILE"
        echo "========================================" >> "$OUTPUT_FILE"
        echo "" >> "$OUTPUT_FILE"
        
        jq -r '.results[] | "ID: \(.id)\n\(. | to_entries | map("\(.key): \(.value)") | join("\n"))\n---\n"' "$JOB_FILE" >> "$OUTPUT_FILE"
        
        echo "✅ Exported to: $OUTPUT_FILE"
        ;;
    
    *)
        echo "❌ Unknown format: $FORMAT"
        echo "Supported formats: json, csv, txt"
        exit 1
        ;;
esac

echo ""
echo "📁 File size: $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "📊 Preview:"
head -n 10 "$OUTPUT_FILE"
