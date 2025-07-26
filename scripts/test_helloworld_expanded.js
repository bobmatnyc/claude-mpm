#!/usr/bin/env node
/**
 * Test script for the /helloworld hook with expanded command
 */

const { spawn } = require('child_process');
const path = require('path');

// Test event with expanded command
const testEvent = {
  hook_event_name: "UserPromptSubmit",
  prompt: "HELLOWORLD_HOOK_TRIGGER",
  session_id: "test-session",
  cwd: process.cwd()
};

console.log('Testing /helloworld hook with expanded command...');
console.log('Input event:', JSON.stringify(testEvent, null, 2));

// Path to the hook
const hookPath = path.join(__dirname, '..', '.claude', 'hooks', 'helloworld_hook.js');

// Spawn the hook process
const hookProcess = spawn('node', [hookPath], {
  stdio: ['pipe', 'pipe', 'pipe']
});

// Send the event to the hook's stdin
hookProcess.stdin.write(JSON.stringify(testEvent));
hookProcess.stdin.end();

// Collect output
let stdout = '';
let stderr = '';

hookProcess.stdout.on('data', (data) => {
  stdout += data.toString();
});

hookProcess.stderr.on('data', (data) => {
  stderr += data.toString();
});

// Handle completion
hookProcess.on('close', (code) => {
  console.log('\n--- Hook Response ---');
  console.log('Exit code:', code);
  
  if (stderr) {
    console.log('Stderr:', stderr);
  }
  
  try {
    const response = JSON.parse(stdout);
    console.log('Response:', JSON.stringify(response, null, 2));
    
    // Verify the response
    if (response.action === 'block' && response.alternative === 'Hello World') {
      console.log('\n✅ Test PASSED! The hook correctly intercepted expanded command and returned "Hello World"');
    } else {
      console.log('\n❌ Test FAILED! Unexpected response');
    }
  } catch (error) {
    console.log('Failed to parse response:', error);
    console.log('Raw stdout:', stdout);
  }
});