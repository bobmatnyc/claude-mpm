#!/usr/bin/env bash
# Quick test script to send a test event to the Svelte dashboard
# Usage: ./test_dashboard_event.sh

echo "📤 Sending test event to dashboard at http://localhost:8765"
echo ""

# Generate timestamp in ISO 8601 format
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)

# Send test event
curl -X POST http://localhost:8765/api/events \
  -H "Content-Type: application/json" \
  -d '{
    "event": "claude_event",
    "data": {
      "type": "hook",
      "subtype": "user_prompt",
      "timestamp": "'"$TIMESTAMP"'",
      "data": {
        "prompt": "Test event from test_dashboard_event.sh",
        "sessionId": "test-session-'$(date +%s)'"
      },
      "source": "manual_test_script",
      "session_id": "test-session-'$(date +%s)'"
    }
  }'

echo ""
echo ""
echo "✅ Event sent! Check the Svelte dashboard at http://localhost:8765/svelte/"
echo ""
echo "You should see a new event in the stream panel with:"
echo "  - Type: hook"
echo "  - Subtype: user_prompt"
echo "  - Prompt: Test event from test_dashboard_event.sh"
echo ""
