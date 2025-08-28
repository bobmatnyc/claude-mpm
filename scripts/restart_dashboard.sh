#!/bin/bash
# Complete Dashboard Restart Script with Cache Clearing

echo "=== Complete Dashboard Restart with Cache Clearing ==="
echo

# Step 1: Kill all existing processes
echo "1. Stopping existing processes..."
pkill -f "socketio_daemon" 2>/dev/null
pkill -f "claude-mpm dashboard" 2>/dev/null
pkill -f "claude-mpm.*dashboard" 2>/dev/null
sleep 2

# Step 2: Clear Python bytecode cache
echo "2. Clearing Python cache..."
find /Users/masa/Projects/claude-mpm -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /Users/masa/Projects/claude-mpm -type f -name "*.pyc" -delete 2>/dev/null
find /Users/masa/Projects/claude-mpm -type f -name "*.pyo" -delete 2>/dev/null

# Step 3: Clear temporary files
echo "3. Clearing temporary files..."
rm -rf /tmp/claude-mpm-* 2>/dev/null
rm -rf /var/tmp/claude-mpm-* 2>/dev/null

# Step 4: Reinstall to ensure latest code
echo "4. Reinstalling package..."
cd /Users/masa/Projects/claude-mpm
pip install -e . --no-cache-dir --force-reinstall --no-deps

# Step 5: Start the dashboard
echo "5. Starting dashboard..."
./venv/bin/claude-mpm dashboard start --port 8765

echo
echo "=== Dashboard restart complete ==="
echo
echo "IMPORTANT: Clear your browser cache:"
echo "  1. Open Chrome/Safari/Firefox to http://localhost:8765"
echo "  2. Press Cmd+Shift+R (Mac) or Ctrl+Shift+F5 (Windows/Linux) for hard refresh"
echo "  3. Or open Developer Tools (F12), right-click refresh button, select 'Empty Cache and Hard Reload'"
echo