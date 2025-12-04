# Quick Start Guide

## What's Running Now

✅ **NeMo Data Designer Mock API** is running on `http://localhost:8080`

The service is ready to accept synthetic data generation requests!

## Complete the Setup (2 minutes)

### Option 1: Automated Setup (Recommended)

Run in your WSL terminal:

```bash
./setup-mcp.sh
```

This will:
- Install Node.js if needed
- Install MCP server dependencies
- Verify the setup

### Option 2: Manual Setup

```bash
cd mcp-server
npm install
```

## Verify Everything Works

### Test the API:
```bash
curl http://localhost:8080/health
```

Expected response:
```json
{"status":"healthy","service":"nemo-data-designer-mock"}
```

### Test the complete workflow:
```bash
./test-mcp-workflow.sh
```

This demonstrates the full job creation → monitoring → results workflow.

## Use with Kiro

1. **Restart Kiro** (or reconnect MCP server from MCP panel)

2. **Start chatting naturally:**

   > "I need to generate 200 question-answer pairs about machine learning"

   Kiro will:
   - Use `guide_job_creation` to understand your needs
   - Recommend optimal configuration
   - Create the job with `create_synthetic_data_job`
   - Monitor progress with `get_job_status`
   - Retrieve results when complete

3. **Other examples:**

   > "Create synthetic data for a 3-class sentiment classifier"
   
   > "Generate 500 text summarization examples"
   
   > "What's the status of my jobs?"
   
   > "Show me the results from my latest job"

## Architecture

```
┌─────────────────┐
│      Kiro       │  ← You chat here
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   MCP Server    │  ← Translates to API calls
│  (Node.js)      │     Provides guidance
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  NeMo Data      │  ← Generates synthetic data
│  Designer API   │     (Mock for now)
│  (Docker)       │
└─────────────────┘
```

## Available MCP Tools

When you chat with Kiro, these tools work behind the scenes:

1. **guide_job_creation** - Analyzes your request and recommends configuration
2. **create_synthetic_data_job** - Creates the generation job
3. **get_job_status** - Monitors job progress
4. **list_jobs** - Shows all your jobs
5. **get_job_results** - Retrieves generated data
6. **cancel_job** - Stops a running job

## Supported Task Types

- **question_answering** - Q&A pairs for training/evaluation
- **summarization** - Text summarization examples
- **classification** - Labeled examples for classifiers
- **text_generation** - General text generation

## Next Steps

### For Development:
- The mock API is perfect for testing and development
- Jobs complete in ~10 seconds
- Generates realistic sample data

### For Production:
1. Get access to NVIDIA NGC
2. Update `docker-compose.yml` with the real NeMo image
3. Configure GPU access
4. Update `.env` with NGC credentials

## Troubleshooting

**MCP server not connecting?**
- Check Node.js is installed: `node --version`
- Verify dependencies: `cd mcp-server && npm list`
- Check Kiro's MCP panel for error messages

**API not responding?**
- Check container: `docker ps`
- View logs: `docker-compose -f docker-compose.api.yml logs -f`
- Restart: `docker-compose -f docker-compose.api.yml restart`

**Need help?**
- See `USAGE_GUIDE.md` for detailed examples
- See `STATUS.md` for current setup status
- Check `README.md` for full documentation

## Files Overview

- `docker-compose.api.yml` - Mock API service
- `mcp-server/index.js` - MCP server implementation
- `.kiro/settings/mcp.json` - Kiro MCP configuration
- `setup-mcp.sh` - Automated setup script
- `test-api.sh` - API testing script
- `test-mcp-workflow.sh` - Full workflow demo

---

**You're all set!** Just run `./setup-mcp.sh` and restart Kiro to start generating synthetic data through natural conversation.
