#!/bin/bash
# Test script to verify Code Tree fixes

echo "Testing Code Tree fixes for claude-mpm..."
echo "========================================="
echo ""
echo "Two issues were fixed:"
echo "1. Code discovery now uses the selected working directory (not root /)"
echo "2. Circular/radial tree layout is now implemented"
echo ""
echo "Starting dashboard..."

# Start the dashboard
./scripts/claude-mpm dashboard &
DASHBOARD_PID=$!

echo "Dashboard started with PID: $DASHBOARD_PID"
echo ""
echo "Please open http://localhost:8765 in your browser"
echo ""
echo "Testing steps:"
echo "1. Select a working directory using the 'Change' button"
echo "2. Click on the 'Code' tab"
echo "3. Verify that discovery only shows files from your selected directory"
echo "4. Verify the circular/radial tree visualization appears"
echo "5. Use the 'Switch to Linear' button to toggle layouts"
echo "6. Click on directories to expand them (lazy loading)"
echo "7. Click on files to analyze their AST"
echo ""
echo "Press Ctrl+C to stop the dashboard when testing is complete"

# Wait for interrupt
trap "kill $DASHBOARD_PID 2>/dev/null; echo 'Dashboard stopped'; exit 0" INT
wait $DASHBOARD_PID
