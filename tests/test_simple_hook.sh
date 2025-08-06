#!/bin/bash
# Simple test to check if hooks are broadcasting

echo "Testing Socket.IO hook broadcasting..."

# Set environment variables
export CLAUDE_MPM_HOOK_DEBUG=true
export CLAUDE_MPM_SOCKETIO_PORT=8765

# Create a simple test prompt
echo "test" | ./scripts/claude-mpm run -i "Just say 'Hello from Claude'" --non-interactive 2>&1 | grep -E "(emitted|Socket|Hook|broadcast|event)" | head -10

echo -e "\nChecking server logs for recent events..."
tail -5 ~/.claude-mpm/socketio-server.log | grep -E "(event|hook|emit|client)" || echo "No recent events in log"