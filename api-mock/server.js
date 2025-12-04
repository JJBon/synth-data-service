const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const fs = require('fs');
const path = require('path');

const app = express();
app.use(cors());
app.use(express.json());

// In-memory job storage
const jobs = new Map();
const jobsDir = '/jobs';

// Ensure jobs directory exists
if (!fs.existsSync(jobsDir)) {
  fs.mkdirSync(jobsDir, { recursive: true });
}

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', service: 'nemo-data-designer-mock' });
});

// Create job
app.post('/v1/jobs', (req, res) => {
  const { name, task_type, num_samples = 100, config = {} } = req.body;
  
  if (!name || !task_type) {
    return res.status(400).json({ error: 'name and task_type are required' });
  }

  const jobId = uuidv4();
  const job = {
    job_id: jobId,
    name,
    task_type,
    num_samples,
    config,
    status: 'pending',
    progress: 0,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  jobs.set(jobId, job);
  
  // Save job to disk
  fs.writeFileSync(
    path.join(jobsDir, `${jobId}.json`),
    JSON.stringify(job, null, 2)
  );

  // Simulate job processing
  setTimeout(() => {
    job.status = 'running';
    job.progress = 25;
    job.updated_at = new Date().toISOString();
  }, 2000);

  setTimeout(() => {
    job.status = 'running';
    job.progress = 75;
    job.updated_at = new Date().toISOString();
  }, 5000);

  setTimeout(() => {
    job.status = 'completed';
    job.progress = 100;
    job.updated_at = new Date().toISOString();
    job.completed_at = new Date().toISOString();
    
    // Generate mock results
    job.results = generateMockResults(task_type, num_samples, config);
    
    fs.writeFileSync(
      path.join(jobsDir, `${jobId}.json`),
      JSON.stringify(job, null, 2)
    );
  }, 10000);

  res.status(201).json({
    job_id: jobId,
    status: job.status,
    message: `Job "${name}" created successfully`,
  });
});

// Get job status
app.get('/v1/jobs/:job_id', (req, res) => {
  const { job_id } = req.params;
  const job = jobs.get(job_id);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  res.json(job);
});

// List jobs
app.get('/v1/jobs', (req, res) => {
  const { status, limit = 10 } = req.query;
  
  let jobList = Array.from(jobs.values());
  
  if (status) {
    jobList = jobList.filter(job => job.status === status);
  }
  
  jobList = jobList.slice(0, parseInt(limit));

  res.json({
    total: jobList.length,
    jobs: jobList,
  });
});

// Get job results
app.get('/v1/jobs/:job_id/results', (req, res) => {
  const { job_id } = req.params;
  const job = jobs.get(job_id);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  if (job.status !== 'completed') {
    return res.status(400).json({ 
      error: 'Job not completed yet',
      status: job.status,
      progress: job.progress 
    });
  }

  res.json({
    job_id,
    results: job.results,
    num_samples: job.num_samples,
  });
});

// Cancel job
app.post('/v1/jobs/:job_id/cancel', (req, res) => {
  const { job_id } = req.params;
  const job = jobs.get(job_id);

  if (!job) {
    return res.status(404).json({ error: 'Job not found' });
  }

  if (job.status === 'completed' || job.status === 'failed') {
    return res.status(400).json({ 
      error: `Cannot cancel job with status: ${job.status}` 
    });
  }

  job.status = 'cancelled';
  job.updated_at = new Date().toISOString();

  res.json({
    job_id,
    status: job.status,
    message: 'Job cancelled successfully',
  });
});

// Generate mock synthetic data based on task type
function generateMockResults(taskType, numSamples, config) {
  const results = [];
  const sampleCount = Math.min(numSamples, 10); // Return first 10 for demo

  switch (taskType) {
    case 'question_answering':
      for (let i = 0; i < sampleCount; i++) {
        results.push({
          id: i + 1,
          question: `What is an example question about ${config.domain || 'general knowledge'} #${i + 1}?`,
          answer: `This is a ${config.difficulty || 'medium'} difficulty answer providing detailed information about the topic.`,
          context: `Context for question ${i + 1}`,
        });
      }
      break;

    case 'summarization':
      for (let i = 0; i < sampleCount; i++) {
        results.push({
          id: i + 1,
          source_text: `This is a ${config.source_length || 'medium'} length source document #${i + 1} that needs to be summarized. It contains multiple sentences with various information.`,
          summary: `${config.style || 'Abstractive'} summary of document ${i + 1}.`,
        });
      }
      break;

    case 'classification':
      const labels = config.class_labels || ['class_1', 'class_2', 'class_3'];
      for (let i = 0; i < sampleCount; i++) {
        results.push({
          id: i + 1,
          text: `Sample text for classification #${i + 1}`,
          label: labels[i % labels.length],
          confidence: 0.85 + Math.random() * 0.15,
        });
      }
      break;

    case 'text_generation':
      for (let i = 0; i < sampleCount; i++) {
        results.push({
          id: i + 1,
          text: `Generated ${config.style || 'general'} text sample #${i + 1} with ${config.length || 'medium'} length.`,
          metadata: {
            style: config.style,
            topics: config.topics,
          },
        });
      }
      break;

    default:
      for (let i = 0; i < sampleCount; i++) {
        results.push({
          id: i + 1,
          data: `Generic synthetic data sample #${i + 1}`,
        });
      }
  }

  return results;
}

const PORT = process.env.PORT || 8080;
app.listen(PORT, '0.0.0.0', () => {
  console.log(`NeMo Data Designer Mock API running on port ${PORT}`);
  console.log(`Health check: http://localhost:${PORT}/health`);
});
