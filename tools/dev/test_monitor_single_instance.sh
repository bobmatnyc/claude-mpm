#!/usr/bin/env bash
# Test script for single-instance monitor enforcement
#
# This script verifies:
# 1. First monitor starts on port 8765
# 2. Second monitor reuses existing instance
# 3. Explicit --port uses that port or fails
# 4. No auto-increment port selection

set -e

echo "=== Testing Monitor Single Instance Enforcement ==="
echo

# Cleanup function
cleanup() {
    echo "Cleaning up test processes..."
    pkill -f "claude-mpm.*monitor" || true
    sleep 2
}

trap cleanup EXIT

# Test 1: Start first monitor on default port 8765
echo "Test 1: Starting first monitor on default port 8765..."
claude-mpm-monitor --no-browser --background &
FIRST_PID=$!
sleep 3

# Verify it's running on 8765
if curl -s http://localhost:8765/health | grep -q "claude-mpm-monitor"; then
    echo "✅ Test 1 PASSED: Monitor running on port 8765"
else
    echo "❌ Test 1 FAILED: Monitor not running on port 8765"
    exit 1
fi

# Test 2: Try to start second monitor (should reuse existing)
echo
echo "Test 2: Attempting to start second monitor (should reuse existing)..."
OUTPUT=$(claude-mpm-monitor --no-browser 2>&1 || true)

if echo "$OUTPUT" | grep -q "already running"; then
    echo "✅ Test 2 PASSED: Second monitor detected existing instance"
else
    echo "❌ Test 2 FAILED: Second monitor did not detect existing instance"
    echo "Output: $OUTPUT"
    exit 1
fi

# Test 3: Stop first monitor
echo
echo "Test 3: Stopping first monitor..."
pkill -f "claude-mpm.*monitor" || true
sleep 2

# Verify port 8765 is now free
if ! curl -s http://localhost:8765/health >/dev/null 2>&1; then
    echo "✅ Test 3 PASSED: Port 8765 is now free"
else
    echo "❌ Test 3 FAILED: Port 8765 still in use"
    exit 1
fi

# Test 4: Start monitor on explicit port 9000
echo
echo "Test 4: Starting monitor on explicit port 9000..."
claude-mpm-monitor --port 9000 --no-browser --background &
sleep 3

if curl -s http://localhost:9000/health | grep -q "claude-mpm-monitor"; then
    echo "✅ Test 4 PASSED: Monitor running on port 9000"
else
    echo "❌ Test 4 FAILED: Monitor not running on port 9000"
    exit 1
fi

# Test 5: Try to start another monitor on same port (should fail)
echo
echo "Test 5: Attempting to start second monitor on port 9000 (should fail or reuse)..."
OUTPUT=$(claude-mpm-monitor --port 9000 --no-browser 2>&1 || true)

if echo "$OUTPUT" | grep -q -E "(already running|already in use)"; then
    echo "✅ Test 5 PASSED: Port conflict detected correctly"
else
    echo "❌ Test 5 FAILED: Port conflict not detected"
    echo "Output: $OUTPUT"
    exit 1
fi

echo
echo "=== All Tests Passed! ==="
echo
echo "Summary:"
echo "✅ Single instance enforcement working"
echo "✅ Existing instance reuse working"
echo "✅ Explicit port specification working"
echo "✅ Port conflict detection working"
echo "✅ No auto-increment port selection"
