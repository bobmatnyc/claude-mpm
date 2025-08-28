#!/bin/bash
# Test script to verify dashboard discovery is working

echo "Starting dashboard discovery test..."
echo "=================================="

# Kill any existing dashboard processes
pkill -f "claude-mpm dashboard" 2>/dev/null

# Start the dashboard in the background
echo "Starting dashboard server..."
./scripts/claude-mpm dashboard serve --port 8765 &
DASHBOARD_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Open browser to test
echo "Opening browser to test..."
open "http://localhost:8765"

echo ""
echo "Test steps:"
echo "1. Click on the 'Code' tab"
echo "2. Check if the tree shows ONLY project directories"
echo "3. You should NOT see /Users or any system paths"
echo "4. The tree should start with 'claude-mpm' as the root"
echo ""
echo "Press Ctrl+C to stop the dashboard when done testing"

# Wait for user to test
wait $DASHBOARD_PID