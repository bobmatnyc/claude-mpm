#!/bin/bash
# Test script for tool_call_id correlation
#
# This script demonstrates the tool_call_id correlation by sending test events
# through the dashboard event system.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "🧪 Testing tool_call_id correlation implementation"
echo "=================================================="
echo ""

# Function to send test event
send_test_event() {
    local event_type="$1"
    local tool_call_id="$2"
    local tool_name="$3"

    echo "📤 Sending $event_type event for $tool_name (correlation: ${tool_call_id:0:8}...)"

    curl -s -X POST http://localhost:8765/test/event \
        -H "Content-Type: application/json" \
        -d "{
            \"type\": \"hook\",
            \"subtype\": \"$event_type\",
            \"correlation_id\": \"$tool_call_id\",
            \"data\": {
                \"tool_name\": \"$tool_name\",
                \"tool_call_id\": \"$tool_call_id\",
                \"session_id\": \"test-session-123\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"
            }
        }" > /dev/null

    echo "   ✅ Sent"
}

# Check if server is running
if ! curl -s http://localhost:8765/health > /dev/null 2>&1; then
    echo "❌ Error: Dashboard server not running on localhost:8765"
    echo "   Start it with: claude-mpm run"
    exit 1
fi

echo "✅ Dashboard server is running"
echo ""

# Generate unique tool_call_id for this test
TOOL_CALL_ID="test-$(uuidgen | tr '[:upper:]' '[:lower:]')"

echo "📝 Generated tool_call_id: $TOOL_CALL_ID"
echo ""

# Simulate tool execution sequence
echo "🔧 Simulating Read tool execution..."
send_test_event "pre_tool" "$TOOL_CALL_ID" "Read"

echo "   ⏳ Simulating tool execution delay..."
sleep 0.5

send_test_event "post_tool" "$TOOL_CALL_ID" "Read"

echo ""
echo "✅ Test complete!"
echo ""
echo "📊 Check the dashboard at http://localhost:8765 to verify:"
echo "   1. Both events have the same correlation_id: $TOOL_CALL_ID"
echo "   2. Pre_tool and post_tool events are visually linked"
echo "   3. Duration is calculated between events"
echo ""
echo "🔍 You can also check the browser console for event details"
