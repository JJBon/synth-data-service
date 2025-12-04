# Quick Reference Card

## 🎯 One-Line Summary
Chat with Kiro to generate synthetic data - it's that simple!

## ✅ Status
- Docker API: ✅ Running on port 8080
- MCP Server: ✅ Tested and ready
- Configuration: ✅ Loaded in Kiro

## 🚀 To Start Using
1. Restart Kiro
2. Chat naturally about data needs

## 💬 Example Prompts

| What You Want | What To Say |
|---------------|-------------|
| Q&A pairs | "Generate 200 Q&A pairs about Python" |
| Classification data | "Create sentiment classifier data with 3 classes" |
| Summaries | "Generate 500 text summarization examples" |
| Check status | "What's the status of my jobs?" |
| Get results | "Show me the results from my latest job" |

## 🔧 MCP Tools (Behind the Scenes)

1. **guide_job_creation** - Analyzes your request
2. **create_synthetic_data_job** - Creates the job
3. **get_job_status** - Monitors progress
4. **list_jobs** - Lists all jobs
5. **get_job_results** - Gets the data
6. **cancel_job** - Cancels jobs

## 📊 Task Types

- `question_answering` - Q&A pairs
- `summarization` - Text summaries
- `classification` - Labeled examples
- `text_generation` - General text

## 🛠️ Quick Commands

```bash
# Check API
curl http://localhost:8080/health

# View logs
docker-compose -f docker-compose.api.yml logs -f

# Restart
docker-compose -f docker-compose.api.yml restart

# Test
node test-mcp-integration.js
```

## 📚 Documentation

- `FINAL_STATUS.md` - Complete status
- `TEST_RESULTS.md` - Test details
- `USAGE_GUIDE.md` - Usage examples
- `PROJECT_SUMMARY.md` - Full overview

## 🎉 You're Ready!

Just restart Kiro and start chatting!
