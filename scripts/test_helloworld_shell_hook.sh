#!/bin/bash
# Test script for the shell-wrapped /helloworld hook

echo "Testing /helloworld hook with shell wrapper..."

# Test event
TEST_EVENT='{
  "hook_event_name": "UserPromptSubmit",
  "prompt": "/helloworld",
  "session_id": "test-session",
  "cwd": "'$(pwd)'"
}'

echo "Input event: $TEST_EVENT"
echo "---"

# Run the hook
RESPONSE=$(echo "$TEST_EVENT" | /Users/masa/Projects/claude-mpm/.claude/hooks/helloworld_hook.sh)
EXIT_CODE=$?

echo "Exit code: $EXIT_CODE"
echo "Response: $RESPONSE"

# Check if response is valid JSON and contains expected fields
if echo "$RESPONSE" | python3 -c "import json, sys; data = json.load(sys.stdin); sys.exit(0 if data.get('action') == 'block' and data.get('alternative') == 'Hello World' else 1)" 2>/dev/null; then
    echo "✅ Test PASSED! Hook correctly intercepted /helloworld and returned 'Hello World'"
else
    echo "❌ Test FAILED!"
fi