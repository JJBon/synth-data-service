#!/usr/bin/env node

const axios = require('axios');

const API_URL = 'http://localhost:8080';

console.log('🎬 NeMo Data Designer - Use Case Demonstrations\n');
console.log('='.repeat(70));

// Helper function to wait
const wait = (ms) => new Promise(resolve => setTimeout(resolve, ms));

// Helper to display results nicely
const display = (title, data) => {
  console.log(`\n${'='.repeat(70)}`);
  console.log(`📋 ${title}`);
  console.log('='.repeat(70));
  console.log(JSON.stringify(data, null, 2));
};

async function runUseCases() {
  try {
    // USE CASE 1: Generate Q&A pairs about Python
    console.log('\n\n🎯 USE CASE 1: Generate 200 Q&A pairs about Python programming');
    console.log('-'.repeat(70));
    
    console.log('\n💭 User says: "I need 200 Q&A pairs about Python programming"');
    console.log('\n🤖 Kiro analyzes request using guide_job_creation...');
    
    const guidance1 = {
      user_goal: "I need 200 Q&A pairs about Python programming",
      recommendations: [
        {
          task_type: "question_answering",
          description: "Generate question-answer pairs for training or evaluation",
          suggested_config: {
            domain: "Python programming",
            difficulty: "medium",
            answer_length: "medium"
          }
        }
      ],
      next_steps: [
        "1. Task type: question_answering",
        "2. Samples: 200",
        "3. Domain: Python programming",
        "4. Creating job now..."
      ]
    };
    
    display('Guidance Provided', guidance1);
    
    console.log('\n🚀 Creating job with recommended configuration...');
    const job1 = await axios.post(`${API_URL}/v1/jobs`, {
      name: 'python-qa-dataset',
      task_type: 'question_answering',
      num_samples: 200,
      config: {
        domain: 'python_programming',
        difficulty: 'medium',
        answer_length: 'medium'
      }
    });
    
    display('Job Created', {
      job_id: job1.data.job_id,
      status: job1.data.status,
      message: job1.data.message
    });
    
    const jobId1 = job1.data.job_id;
    
    // Monitor progress
    console.log('\n📊 Monitoring job progress...');
    for (let i = 0; i < 3; i++) {
      await wait(3000);
      const status = await axios.get(`${API_URL}/v1/jobs/${jobId1}`);
      console.log(`   Progress: ${status.data.progress}% - Status: ${status.data.status}`);
    }
    
    // Wait for completion
    console.log('\n⏳ Waiting for job to complete...');
    await wait(5000);
    
    const results1 = await axios.get(`${API_URL}/v1/jobs/${jobId1}/results`);
    display('Results Preview (First 3 samples)', {
      job_id: results1.data.job_id,
      total_samples: results1.data.num_samples,
      samples: results1.data.results.slice(0, 3)
    });
    
    console.log('\n✅ USE CASE 1 COMPLETE: Generated 200 Python Q&A pairs!');
    
    // USE CASE 2: Generate sentiment classification data
    console.log('\n\n🎯 USE CASE 2: Generate sentiment classifier data with 3 classes');
    console.log('-'.repeat(70));
    
    console.log('\n💭 User says: "Create sentiment classifier data with 3 classes"');
    console.log('\n🤖 Kiro analyzes request using guide_job_creation...');
    
    const guidance2 = {
      user_goal: "Create sentiment classifier data with 3 classes",
      recommendations: [
        {
          task_type: "classification",
          description: "Generate labeled examples for classification tasks",
          suggested_config: {
            num_classes: 3,
            class_labels: ["positive", "negative", "neutral"],
            balance: "balanced distribution"
          }
        }
      ],
      next_steps: [
        "1. Task type: classification",
        "2. Classes: 3 (positive, negative, neutral)",
        "3. Samples: 1000 (recommended for balanced training)",
        "4. Creating job now..."
      ]
    };
    
    display('Guidance Provided', guidance2);
    
    console.log('\n🚀 Creating classification job...');
    const job2 = await axios.post(`${API_URL}/v1/jobs`, {
      name: 'sentiment-classifier-data',
      task_type: 'classification',
      num_samples: 1000,
      config: {
        num_classes: 3,
        class_labels: ['positive', 'negative', 'neutral'],
        balance: 'balanced'
      }
    });
    
    display('Job Created', {
      job_id: job2.data.job_id,
      status: job2.data.status,
      message: job2.data.message
    });
    
    const jobId2 = job2.data.job_id;
    
    // Monitor progress
    console.log('\n📊 Monitoring job progress...');
    for (let i = 0; i < 3; i++) {
      await wait(3000);
      const status = await axios.get(`${API_URL}/v1/jobs/${jobId2}`);
      console.log(`   Progress: ${status.data.progress}% - Status: ${status.data.status}`);
    }
    
    console.log('\n⏳ Waiting for job to complete...');
    await wait(5000);
    
    const results2 = await axios.get(`${API_URL}/v1/jobs/${jobId2}/results`);
    display('Results Preview (First 3 samples)', {
      job_id: results2.data.job_id,
      total_samples: results2.data.num_samples,
      samples: results2.data.results.slice(0, 3)
    });
    
    console.log('\n✅ USE CASE 2 COMPLETE: Generated 1000 sentiment classification examples!');
    
    // USE CASE 3: Generate text summarization examples
    console.log('\n\n🎯 USE CASE 3: Generate 500 text summarization examples');
    console.log('-'.repeat(70));
    
    console.log('\n💭 User says: "Generate 500 text summarization examples"');
    console.log('\n🤖 Kiro analyzes request using guide_job_creation...');
    
    const guidance3 = {
      user_goal: "Generate 500 text summarization examples",
      recommendations: [
        {
          task_type: "summarization",
          description: "Generate text summarization examples",
          suggested_config: {
            source_length: "long",
            summary_length: "short",
            style: "abstractive"
          }
        }
      ],
      next_steps: [
        "1. Task type: summarization",
        "2. Samples: 500",
        "3. Style: abstractive",
        "4. Creating job now..."
      ]
    };
    
    display('Guidance Provided', guidance3);
    
    console.log('\n🚀 Creating summarization job...');
    const job3 = await axios.post(`${API_URL}/v1/jobs`, {
      name: 'text-summarization-dataset',
      task_type: 'summarization',
      num_samples: 500,
      config: {
        source_length: 'long',
        summary_length: 'short',
        style: 'abstractive'
      }
    });
    
    display('Job Created', {
      job_id: job3.data.job_id,
      status: job3.data.status,
      message: job3.data.message
    });
    
    const jobId3 = job3.data.job_id;
    
    // Monitor progress
    console.log('\n📊 Monitoring job progress...');
    for (let i = 0; i < 3; i++) {
      await wait(3000);
      const status = await axios.get(`${API_URL}/v1/jobs/${jobId3}`);
      console.log(`   Progress: ${status.data.progress}% - Status: ${status.data.status}`);
    }
    
    console.log('\n⏳ Waiting for job to complete...');
    await wait(5000);
    
    const results3 = await axios.get(`${API_URL}/v1/jobs/${jobId3}/results`);
    display('Results Preview (First 2 samples)', {
      job_id: results3.data.job_id,
      total_samples: results3.data.num_samples,
      samples: results3.data.results.slice(0, 2)
    });
    
    console.log('\n✅ USE CASE 3 COMPLETE: Generated 500 summarization examples!');
    
    // USE CASE 4: Check status of all jobs
    console.log('\n\n🎯 USE CASE 4: Check status of all jobs');
    console.log('-'.repeat(70));
    
    console.log('\n💭 User says: "What\'s the status of my jobs?"');
    console.log('\n🤖 Kiro uses list_jobs to retrieve all jobs...');
    
    const allJobs = await axios.get(`${API_URL}/v1/jobs?limit=10`);
    
    display('All Jobs', {
      total: allJobs.data.total,
      jobs: allJobs.data.jobs.map(job => ({
        name: job.name,
        task_type: job.task_type,
        status: job.status,
        progress: job.progress + '%',
        num_samples: job.num_samples
      }))
    });
    
    console.log('\n✅ USE CASE 4 COMPLETE: Listed all jobs!');
    
    // Final Summary
    console.log('\n\n' + '='.repeat(70));
    console.log('🎉 ALL USE CASES COMPLETED SUCCESSFULLY!');
    console.log('='.repeat(70));
    
    console.log('\n📊 Summary:');
    console.log('   ✅ Generated 200 Python Q&A pairs');
    console.log('   ✅ Generated 1000 sentiment classification examples');
    console.log('   ✅ Generated 500 text summarization examples');
    console.log('   ✅ Listed all jobs and their status');
    
    console.log('\n💡 This is exactly what happens when you chat with Kiro!');
    console.log('   The MCP server handles all these API calls automatically.');
    console.log('   You just use natural language, and Kiro does the rest.');
    
    console.log('\n🚀 Ready to use with Kiro:');
    console.log('   1. Restart Kiro');
    console.log('   2. Start chatting about your data needs');
    console.log('   3. Let the MCP server handle everything!');
    
    console.log('\n' + '='.repeat(70));
    
  } catch (error) {
    console.error('\n❌ Error:', error.message);
    if (error.response) {
      console.error('Response:', error.response.data);
    }
  }
}

// Run all use cases
runUseCases();
