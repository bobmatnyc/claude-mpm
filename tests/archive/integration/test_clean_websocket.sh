#!/bin/bash
# Clean test of WebSocket logging

echo "🧹 Cleaning up old WebSocket servers..."
echo ""

# Kill any existing servers on port 8765
lsof -ti :8765 | xargs -r kill 2>/dev/null || true

# Remove old persistent server scripts
rm -f ~/.claude-mpm/websocket_server_*.py

echo "✅ Cleanup complete"
echo ""
echo "🚀 Starting claude-mpm with monitor mode..."
echo "   This will create a fresh WebSocket server with logging"
echo ""
echo "📊 Check the dashboard for:"
echo "   - Log messages in Console Output"
echo "   - Real-time events"
echo ""

# Start with subprocess mode to ensure logging works
python -m claude_mpm run --monitor --launch-method subprocess --logging INFO
