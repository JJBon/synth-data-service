#!/usr/bin/env node

// Test script for MCP server
const { spawn } = require('child_process');

console.log('Testing NeMo Data Designer MCP Server...\n');

// Start the MCP server
const server = spawn('node', ['mcp-server/index.js'], {
  env: { ...process.env, NEMO_DATA_DESIGNER_URL: 'http://localhost:8080' }
});

let output = '';

server.stdout.on('data', (data) => {
  output += data.toString();
  console.log('STDOUT:', data.toString());
});

server.stderr.on('data', (data) => {
  console.log('STDERR:', data.toString());
});

// Send a list tools request
setTimeout(() => {
  console.log('\n📤 Sending ListTools request...\n');
  
  const request = {
    jsonrpc: '2.0',
    id: 1,
    method: 'tools/list',
    params: {}
  };
  
  server.stdin.write(JSON.stringify(request) + '\n');
}, 1000);

// Send a test tool call
setTimeout(() => {
  console.log('\n📤 Sending guide_job_creation test...\n');
  
  const request = {
    jsonrpc: '2.0',
    id: 2,
    method: 'tools/call',
    params: {
      name: 'guide_job_creation',
      arguments: {
        user_goal: 'I need to generate question-answer pairs about Python programming'
      }
    }
  };
  
  server.stdin.write(JSON.stringify(request) + '\n');
}, 2000);

// Cleanup after tests
setTimeout(() => {
  console.log('\n✅ Test complete! Shutting down...\n');
  server.kill();
  process.exit(0);
}, 4000);

server.on('error', (error) => {
  console.error('❌ Error starting server:', error);
  process.exit(1);
});

server.on('close', (code) => {
  console.log(`\nServer process exited with code ${code}`);
});
