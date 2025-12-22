#!/usr/bin/env node

/**
 * Test script to check if file tracking is working in the claude-mpm dashboard
 * Connects to the SSE stream and looks for file-related events
 */

const http = require('http');

console.log('Connecting to claude-mpm dashboard SSE stream...');
console.log('URL: http://localhost:8765/api/stream');
console.log('---');

const req = http.get('http://localhost:8765/api/stream', (res) => {
  console.log(`Status: ${res.statusCode}`);
  console.log(`Headers:`, res.headers);
  console.log('---');
  console.log('Listening for events...\n');

  let buffer = '';
  let eventCount = 0;
  let fileEventCount = 0;

  res.on('data', (chunk) => {
    buffer += chunk.toString();

    // Process complete events (separated by double newlines)
    const events = buffer.split('\n\n');
    buffer = events.pop() || ''; // Keep incomplete event in buffer

    events.forEach(eventStr => {
      if (!eventStr.trim()) return;

      eventCount++;

      // Parse SSE format
      const lines = eventStr.split('\n');
      let eventType = 'message';
      let data = '';

      lines.forEach(line => {
        if (line.startsWith('event: ')) {
          eventType = line.substring(7);
        } else if (line.startsWith('data: ')) {
          data = line.substring(6);
        }
      });

      if (data) {
        try {
          const parsed = JSON.parse(data);

          // Check if this is a file-related event
          const hasFilePath = checkForFilePath(parsed);

          if (hasFilePath) {
            fileEventCount++;
            console.log(`\n[FILE EVENT #${fileEventCount}]`);
            console.log(`Event type: ${eventType}`);
            console.log(`Event subtype: ${parsed.subtype || 'N/A'}`);
            console.log(`File path: ${hasFilePath}`);
            console.log(`Tool: ${parsed.data?.tool_name || parsed.data?.tool || 'N/A'}`);
            console.log(`Timestamp: ${parsed.timestamp}`);
            console.log('---');
          }

          // Show summary periodically
          if (eventCount % 10 === 0) {
            console.log(`\n[SUMMARY] Processed ${eventCount} events, found ${fileEventCount} file events`);
          }
        } catch (e) {
          console.error('Failed to parse event data:', e.message);
        }
      }
    });
  });

  res.on('end', () => {
    console.log('\n[STREAM ENDED]');
    console.log(`Total events: ${eventCount}`);
    console.log(`File events: ${fileEventCount}`);
  });
});

req.on('error', (e) => {
  console.error('Request error:', e.message);
  process.exit(1);
});

// Helper function to check for file paths in event data
function checkForFilePath(event) {
  if (!event.data) return null;

  const data = event.data;

  // Check hook_input_data.params (new hook structure)
  if (data.hook_input_data?.params?.file_path) {
    return data.hook_input_data.params.file_path;
  }
  if (data.hook_input_data?.params?.path) {
    return data.hook_input_data.params.path;
  }

  // Check tool_parameters (old structure)
  if (data.tool_parameters?.file_path) {
    return data.tool_parameters.file_path;
  }
  if (data.tool_parameters?.path) {
    return data.tool_parameters.path;
  }

  // Check direct properties
  if (data.file_path) {
    return data.file_path;
  }
  if (data.path) {
    return data.path;
  }

  // Check parameters (for pre_tool events)
  if (data.parameters?.file_path) {
    return data.parameters.file_path;
  }
  if (data.parameters?.path) {
    return data.parameters.path;
  }

  return null;
}

// Terminate after 10 seconds
setTimeout(() => {
  console.log('\n[TIMEOUT] Test complete after 10 seconds');
  req.destroy();
  process.exit(0);
}, 10000);
