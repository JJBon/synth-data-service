#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from '@modelcontextprotocol/sdk/types.js';
import axios from 'axios';

const NEMO_API_URL = process.env.NEMO_DATA_DESIGNER_URL || 'http://localhost:8080';

class NeMoDataDesignerServer {
  constructor() {
    this.server = new Server(
      {
        name: 'nemo-data-designer-mcp',
        version: '1.0.0',
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupToolHandlers();
    this.server.onerror = (error) => console.error('[MCP Error]', error);
    process.on('SIGINT', async () => {
      await this.server.close();
      process.exit(0);
    });
  }

  setupToolHandlers() {
    this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
      tools: [
        {
          name: 'create_synthetic_data_job',
          description: 'Create a new synthetic data generation job in NeMo Data Designer. Guide users through specifying task type, data format, and generation parameters.',
          inputSchema: {
            type: 'object',
            properties: {
              job_name: {
                type: 'string',
                description: 'Name for the synthetic data generation job',
              },
              task_type: {
                type: 'string',
                description: 'Type of task (e.g., "text_generation", "question_answering", "summarization", "classification")',
              },
              num_samples: {
                type: 'number',
                description: 'Number of synthetic samples to generate',
                default: 100,
              },
              config: {
                type: 'object',
                description: 'Additional configuration parameters for the job (model settings, prompts, etc.)',
              },
            },
            required: ['job_name', 'task_type'],
          },
        },
        {
          name: 'get_job_status',
          description: 'Get the status of a synthetic data generation job',
          inputSchema: {
            type: 'object',
            properties: {
              job_id: {
                type: 'string',
                description: 'The ID of the job to check',
              },
            },
            required: ['job_id'],
          },
        },
        {
          name: 'list_jobs',
          description: 'List all synthetic data generation jobs',
          inputSchema: {
            type: 'object',
            properties: {
              status: {
                type: 'string',
                description: 'Filter by status (e.g., "pending", "running", "completed", "failed")',
              },
              limit: {
                type: 'number',
                description: 'Maximum number of jobs to return',
                default: 10,
              },
            },
          },
        },
        {
          name: 'get_job_results',
          description: 'Retrieve the generated synthetic data from a completed job',
          inputSchema: {
            type: 'object',
            properties: {
              job_id: {
                type: 'string',
                description: 'The ID of the completed job',
              },
            },
            required: ['job_id'],
          },
        },
        {
          name: 'cancel_job',
          description: 'Cancel a running synthetic data generation job',
          inputSchema: {
            type: 'object',
            properties: {
              job_id: {
                type: 'string',
                description: 'The ID of the job to cancel',
              },
            },
            required: ['job_id'],
          },
        },
        {
          name: 'guide_job_creation',
          description: 'Get interactive guidance for creating a synthetic data generation job. Returns questions and recommendations based on user needs.',
          inputSchema: {
            type: 'object',
            properties: {
              user_goal: {
                type: 'string',
                description: 'Description of what kind of synthetic data the user wants to generate',
              },
              context: {
                type: 'object',
                description: 'Additional context about the use case',
              },
            },
            required: ['user_goal'],
          },
        },
      ],
    }));

    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      try {
        switch (name) {
          case 'create_synthetic_data_job':
            return await this.createJob(args);
          case 'get_job_status':
            return await this.getJobStatus(args);
          case 'list_jobs':
            return await this.listJobs(args);
          case 'get_job_results':
            return await this.getJobResults(args);
          case 'cancel_job':
            return await this.cancelJob(args);
          case 'guide_job_creation':
            return await this.guideJobCreation(args);
          default:
            throw new Error(`Unknown tool: ${name}`);
        }
      } catch (error) {
        return {
          content: [
            {
              type: 'text',
              text: `Error: ${error.message}`,
            },
          ],
          isError: true,
        };
      }
    });
  }

  async createJob(args) {
    const { job_name, task_type, num_samples = 100, config = {} } = args;

    const jobPayload = {
      name: job_name,
      task_type,
      num_samples,
      config,
    };

    const response = await axios.post(`${NEMO_API_URL}/v1/jobs`, jobPayload);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            success: true,
            job_id: response.data.job_id,
            status: response.data.status,
            message: `Job "${job_name}" created successfully. Job ID: ${response.data.job_id}`,
          }, null, 2),
        },
      ],
    };
  }

  async getJobStatus(args) {
    const { job_id } = args;
    const response = await axios.get(`${NEMO_API_URL}/v1/jobs/${job_id}`);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            job_id: response.data.job_id,
            name: response.data.name,
            status: response.data.status,
            progress: response.data.progress,
            created_at: response.data.created_at,
            updated_at: response.data.updated_at,
          }, null, 2),
        },
      ],
    };
  }

  async listJobs(args) {
    const { status, limit = 10 } = args;
    const params = { limit };
    if (status) params.status = status;

    const response = await axios.get(`${NEMO_API_URL}/v1/jobs`, { params });

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            total: response.data.total,
            jobs: response.data.jobs,
          }, null, 2),
        },
      ],
    };
  }

  async getJobResults(args) {
    const { job_id } = args;
    const response = await axios.get(`${NEMO_API_URL}/v1/jobs/${job_id}/results`);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            job_id,
            results: response.data.results,
            num_samples: response.data.num_samples,
          }, null, 2),
        },
      ],
    };
  }

  async cancelJob(args) {
    const { job_id } = args;
    const response = await axios.post(`${NEMO_API_URL}/v1/jobs/${job_id}/cancel`);

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify({
            success: true,
            job_id,
            status: response.data.status,
            message: `Job ${job_id} has been cancelled.`,
          }, null, 2),
        },
      ],
    };
  }

  async guideJobCreation(args) {
    const { user_goal, context = {} } = args;

    // Provide intelligent guidance based on user goal
    const guidance = {
      user_goal,
      recommendations: [],
      next_steps: [],
    };

    // Analyze user goal and provide recommendations
    const goalLower = user_goal.toLowerCase();

    if (goalLower.includes('question') || goalLower.includes('qa')) {
      guidance.recommendations.push({
        task_type: 'question_answering',
        description: 'Generate question-answer pairs for training or evaluation',
        suggested_config: {
          domain: 'Specify your domain (e.g., medical, legal, technical)',
          difficulty: 'easy, medium, or hard',
          answer_length: 'short, medium, or long',
        },
      });
    }

    if (goalLower.includes('summar')) {
      guidance.recommendations.push({
        task_type: 'summarization',
        description: 'Generate text summarization examples',
        suggested_config: {
          source_length: 'Length of source documents',
          summary_length: 'Desired summary length',
          style: 'abstractive or extractive',
        },
      });
    }

    if (goalLower.includes('classif') || goalLower.includes('categor')) {
      guidance.recommendations.push({
        task_type: 'classification',
        description: 'Generate labeled examples for classification tasks',
        suggested_config: {
          num_classes: 'Number of categories',
          class_labels: 'List of class names',
          balance: 'balanced or imbalanced distribution',
        },
      });
    }

    if (goalLower.includes('generat') || goalLower.includes('text')) {
      guidance.recommendations.push({
        task_type: 'text_generation',
        description: 'Generate diverse text samples',
        suggested_config: {
          style: 'formal, casual, technical, creative',
          length: 'short, medium, or long',
          topics: 'List of topics to cover',
        },
      });
    }

    // If no specific task detected, provide general guidance
    if (guidance.recommendations.length === 0) {
      guidance.recommendations.push({
        message: 'Please specify what type of data you need',
        available_tasks: [
          'question_answering - Q&A pairs',
          'summarization - Text summaries',
          'classification - Labeled examples',
          'text_generation - General text',
        ],
      });
    }

    guidance.next_steps = [
      '1. Choose a task_type from the recommendations',
      '2. Decide how many samples you need (num_samples)',
      '3. Configure task-specific parameters',
      '4. Use create_synthetic_data_job to start generation',
    ];

    return {
      content: [
        {
          type: 'text',
          text: JSON.stringify(guidance, null, 2),
        },
      ],
    };
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.error('NeMo Data Designer MCP server running on stdio');
  }
}

const server = new NeMoDataDesignerServer();
server.run().catch(console.error);
