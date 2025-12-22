#!/bin/bash

# Comprehensive file tracking test for claude-mpm dashboard

echo "=== Claude MPM File Tracking Test ==="
echo "Starting at: $(date)"
echo ""

# Start Socket.IO monitor in background
echo "[1/4] Starting Socket.IO monitor..."
node test_dashboard_socketio.js > /tmp/file_tracking_monitor.log 2>&1 &
MONITOR_PID=$!
echo "Monitor PID: $MONITOR_PID"

# Wait for connection
sleep 4
echo ""

# Check if monitor connected
if grep -q "CONNECTED" /tmp/file_tracking_monitor.log; then
    echo "[2/4] ✓ Monitor connected successfully"
else
    echo "[2/4] ✗ Monitor failed to connect"
    kill $MONITOR_PID 2>/dev/null
    exit 1
fi

echo ""
echo "[3/4] Monitor is active and waiting for file events..."
echo "You can now perform file operations using Claude tools (Read, Write, Edit, Grep, Glob)"
echo "The monitor will capture these events for the next 10 seconds..."
echo ""

# Wait for operations
sleep 10

# Kill monitor
echo ""
echo "[4/4] Stopping monitor..."
kill $MONITOR_PID 2>/dev/null
sleep 2

# Show results
echo ""
echo "=== TEST RESULTS ==="
cat /tmp/file_tracking_monitor.log | grep -A 100 "FILE TRACKING SUMMARY"

echo ""
echo "=== Full monitor log saved to: /tmp/file_tracking_monitor.log ==="
