#!/bin/bash
# Test automatic cleanup functionality

echo "🧪 Testing Automatic WebSocket Cleanup"
echo "====================================="
echo ""

# First, create an old WebSocket server to test cleanup
echo "1️⃣ Creating old WebSocket server process..."
python -c "
import sys
sys.path.insert(0, '.')
from src.claude_mpm.services.websocket_server import WebSocketServer
server = WebSocketServer(port=8765)
server.start()
print('Old server started on port 8765')
import time
while True: time.sleep(1)
" &

OLD_PID=$!
echo "   Started old server with PID: $OLD_PID"
sleep 2

# Check if it's running
if lsof -ti :8765 >/dev/null 2>&1; then
    echo "   ✅ Old server is running"
else
    echo "   ❌ Failed to start old server"
fi

# Create an outdated script
echo "2️⃣ Creating outdated persistent script..."
mkdir -p ~/.claude-mpm
cat > ~/.claude-mpm/websocket_server_8765.py << 'EOF'
#!/usr/bin/env python3
# Old script without logging support
print("This is an outdated script")
EOF
echo "   ✅ Created outdated script"

echo ""
echo "3️⃣ Starting claude-mpm with automatic cleanup..."
echo "   Watch for cleanup messages:"
echo ""

# Run claude-mpm which should clean up automatically
timeout 10s python -m claude_mpm run --manager --non-interactive -i "test cleanup" 2>&1 | grep -E "(Cleaning|Terminated|Removed|Cleanup complete)"

echo ""
echo "4️⃣ Checking cleanup results..."

# Check if old process was killed
if ! kill -0 $OLD_PID 2>/dev/null; then
    echo "   ✅ Old server process was terminated"
else
    echo "   ❌ Old server still running - killing manually"
    kill $OLD_PID
fi

# Check if old script was removed
if [ -f ~/.claude-mpm/websocket_server_8765.py ]; then
    content=$(cat ~/.claude-mpm/websocket_server_8765.py)
    if [[ $content == *"setup_websocket_logging"* ]]; then
        echo "   ✅ Script was updated with logging support"
    else
        echo "   ❌ Old script still exists"
        rm ~/.claude-mpm/websocket_server_8765.py
    fi
else
    echo "   ✅ Old script was removed (will be regenerated)"
fi

echo ""
echo "✅ Cleanup test complete!"