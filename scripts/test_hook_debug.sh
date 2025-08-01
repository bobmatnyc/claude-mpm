#!/bin/bash
# Test hooks with full debug output

echo "=== Testing Claude MPM Hook Broadcasting ==="

# Enable debug mode for better visibility
export CLAUDE_MPM_HOOK_DEBUG=true
export CLAUDE_MPM_SOCKETIO_PORT=8765
export CLAUDE_MPM_DEBUG=1

# Check server status
echo -e "\n1. Checking Socket.IO server status..."
claude-mpm-socketio status

# Check server logs before test
echo -e "\n2. Server log before test:"
tail -5 ~/.claude-mpm/socketio-server.log

# Run Claude with debug output
echo -e "\n3. Running Claude with hooks (debug enabled)..."
echo "test" | ./scripts/claude-mpm run -i "Count to 3" --non-interactive --debug 2>&1 | grep -E "(Hook|hook|emit|Socket|event|broadcast)" | head -20

# Check server logs after test
echo -e "\n4. Server log after test:"
tail -10 ~/.claude-mpm/socketio-server.log | grep -v "Event loop"

# Check if any hook debug logs were created
echo -e "\n5. Checking for hook debug output..."
if [ -f "/tmp/hook-wrapper.log" ]; then
    echo "Hook wrapper log:"
    tail -10 /tmp/hook-wrapper.log
else
    echo "No hook wrapper log found"
fi

# Test direct hook emission
echo -e "\n6. Testing direct Socket.IO emission..."
python -c "
import os
os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
os.environ['CLAUDE_MPM_SOCKETIO_PORT'] = '8765'
import sys
sys.path.insert(0, 'src')
from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler
handler = ClaudeHookHandler()
# Test emission
handler._emit_socketio_event('/hook', 'test', {'message': 'Direct test'})
print('Direct emission test completed')
"