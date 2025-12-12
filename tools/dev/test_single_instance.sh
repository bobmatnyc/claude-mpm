#!/bin/bash
# Test script to verify single-instance monitor behavior

set -e

echo "=== Claude MPM Monitor Single-Instance Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function to run test
run_test() {
    local test_name="$1"
    local expected_result="$2"
    local command="$3"

    echo -e "${YELLOW}Testing: ${test_name}${NC}"

    if eval "$command"; then
        if [ "$expected_result" = "pass" ]; then
            echo -e "${GREEN}✓ PASS${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗ FAIL (expected failure but passed)${NC}"
            ((TESTS_FAILED++))
        fi
    else
        if [ "$expected_result" = "fail" ]; then
            echo -e "${GREEN}✓ PASS (expected failure)${NC}"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}✗ FAIL${NC}"
            ((TESTS_FAILED++))
        fi
    fi
    echo ""
}

# Cleanup function
cleanup() {
    echo "Cleaning up..."
    # Stop any running monitors
    pkill -f "claude-mpm.*monitor" 2>/dev/null || true
    # Remove PID files
    rm -f .claude-mpm/monitor-daemon-*.pid 2>/dev/null || true
    sleep 2
}

# Trap cleanup on exit
trap cleanup EXIT

# Initial cleanup
cleanup

echo "Test 1: Start monitor on default port (8765)"
run_test "First instance starts successfully" "pass" \
    "claude-mpm-monitor --no-browser &
     sleep 3
     curl -s http://localhost:8765/health | grep -q 'claude-mpm-monitor'"

echo "Test 2: Second instance detects existing monitor"
run_test "Second instance reuses existing" "pass" \
    "claude-mpm-monitor --no-browser 2>&1 | grep -q 'already running'"

echo "Test 3: Health endpoint returns correct service"
run_test "Health check returns our service" "pass" \
    "curl -s http://localhost:8765/health | jq -e '.service == \"claude-mpm-monitor\"'"

echo "Test 4: Port 8765 is occupied (can't bind)"
run_test "Port 8765 is in use" "fail" \
    "python3 -c 'import socket; s=socket.socket(); s.bind((\"localhost\", 8765)); s.close()'"

# Stop first instance
echo "Stopping first instance..."
pkill -f "claude-mpm.*monitor" || true
sleep 3

echo "Test 5: Port is released after stop"
run_test "Port 8765 is free after stop" "pass" \
    "python3 -c 'import socket; s=socket.socket(); s.bind((\"localhost\", 8765)); s.close()'"

echo "Test 6: Start with explicit port"
run_test "Start on explicit port 9000" "pass" \
    "claude-mpm-monitor --port 9000 --no-browser &
     sleep 3
     curl -s http://localhost:9000/health | grep -q 'claude-mpm-monitor'"

echo "Test 7: Default port is available again"
run_test "Port 8765 is free (not auto-taken)" "pass" \
    "python3 -c 'import socket; s=socket.socket(); s.bind((\"localhost\", 8765)); s.close()'"

# Stop port 9000 instance
pkill -f "claude-mpm.*monitor" || true
sleep 2

echo "Test 8: Explicit port fails if busy"
run_test "Explicit port fails when busy" "fail" \
    "python3 -c 'import socket, time; s=socket.socket(); s.bind((\"localhost\", 9001)); time.sleep(10)' &
     BLOCKER_PID=\$!
     sleep 1
     claude-mpm-monitor --port 9001 --no-browser
     kill \$BLOCKER_PID 2>/dev/null || true"

echo ""
echo "=== Test Results ==="
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi
