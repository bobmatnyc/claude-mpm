#!/usr/bin/env node

/**
 * Test script to check if file tracking is working in the claude-mpm dashboard
 * Connects to Socket.IO and monitors for file-related events
 */

const { io } = require('socket.io-client');

console.log('Connecting to claude-mpm dashboard Socket.IO...');
console.log('URL: http://localhost:8765');
console.log('---\n');

const socket = io('http://localhost:8765', {
  transports: ['websocket', 'polling']
});

let eventCount = 0;
let fileEventCount = 0;
const fileOperations = new Map();

socket.on('connect', () => {
  console.log('[CONNECTED] Socket.IO connected successfully');
  console.log(`Socket ID: ${socket.id}`);
  console.log('Listening for events...\n');
});

socket.on('disconnect', () => {
  console.log('\n[DISCONNECTED] Socket.IO disconnected');
  printSummary();
});

socket.on('error', (error) => {
  console.error('[ERROR]', error);
});

// Listen for ALL events
socket.onAny((eventName, ...args) => {
  eventCount++;

  const eventData = args[0];

  // Check if this is a file-related event
  const filePath = checkForFilePath(eventData);

  if (filePath) {
    fileEventCount++;
    console.log(`\n[FILE EVENT #${fileEventCount}]`);
    console.log(`Event name: ${eventName}`);
    console.log(`Event subtype: ${eventData?.subtype || 'N/A'}`);
    console.log(`File path: ${filePath}`);
    console.log(`Tool: ${eventData?.data?.tool_name || eventData?.data?.tool || 'N/A'}`);
    console.log(`Timestamp: ${eventData?.timestamp || new Date().toISOString()}`);

    // Track file operations
    if (!fileOperations.has(filePath)) {
      fileOperations.set(filePath, []);
    }
    fileOperations.get(filePath).push({
      event: eventName,
      subtype: eventData?.subtype,
      tool: eventData?.data?.tool_name || eventData?.data?.tool,
      timestamp: eventData?.timestamp || new Date().toISOString()
    });

    console.log('---');
  } else if (eventCount % 50 === 0) {
    // Show progress for non-file events
    console.log(`[PROGRESS] Processed ${eventCount} events (${fileEventCount} file events)`);
  }
});

// Helper function to check for file paths in event data
function checkForFilePath(event) {
  if (!event || !event.data) return null;

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

function printSummary() {
  console.log('\n===== FILE TRACKING SUMMARY =====');
  console.log(`Total events received: ${eventCount}`);
  console.log(`File-related events: ${fileEventCount}`);
  console.log(`Unique files tracked: ${fileOperations.size}`);

  if (fileOperations.size > 0) {
    console.log('\n===== FILES TRACKED =====');
    for (const [filePath, operations] of fileOperations.entries()) {
      console.log(`\n${filePath}:`);
      operations.forEach(op => {
        console.log(`  - ${op.tool || op.event} (${op.subtype}) at ${op.timestamp}`);
      });
    }
  }

  console.log('\n===== TEST COMPLETE =====');
}

// Terminate after 15 seconds
setTimeout(() => {
  console.log('\n[TIMEOUT] Test complete after 15 seconds');
  socket.disconnect();
  setTimeout(() => {
    printSummary();
    process.exit(0);
  }, 500);
}, 15000);

// Handle SIGINT (Ctrl+C)
process.on('SIGINT', () => {
  console.log('\n[INTERRUPTED] Test interrupted by user');
  socket.disconnect();
  setTimeout(() => {
    printSummary();
    process.exit(0);
  }, 500);
});
