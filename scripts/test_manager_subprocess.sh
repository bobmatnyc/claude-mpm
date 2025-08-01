#!/bin/bash
# Test manager mode with subprocess (default) to ensure logging works

echo "🧪 Testing WebSocket Logging with Subprocess Mode"
echo "================================================"
echo ""
echo "This uses subprocess mode (not exec) which should show logs"
echo ""

# Force subprocess mode with --launch-method
python -m claude_mpm run --manager --launch-method subprocess --logging INFO