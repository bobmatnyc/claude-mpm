#!/bin/bash
# Test manager mode with logging

echo "🧪 Testing WebSocket Logging in Dashboard"
echo "=========================================="
echo ""
echo "Starting claude-mpm with:"
echo "  - Manager mode (--manager)"
echo "  - INFO logging level"
echo ""
echo "You should see:"
echo "  ✓ Dashboard opens in browser"
echo "  ✓ Log messages appear in Console Output section"
echo "  ✓ Different log levels with color coding"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run with manager mode and INFO logging
python -m claude_mpm run --manager --logging INFO