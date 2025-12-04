#!/bin/bash
# Test script for daemon startup reliability
# Tests multiple consecutive daemon starts on different ports

set -e

PROJECT_ROOT="/Users/masa/Projects/claude-mpm"
PYTHON="${PROJECT_ROOT}/venv/bin/python"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
SUCCESS_COUNT=0
FAIL_COUNT=0
TOTAL_TESTS=20

echo "======================================"
echo "Daemon Startup Reliability Test"
echo "Testing $TOTAL_TESTS daemon starts"
echo "======================================"
echo ""

# Cleanup function
cleanup_daemon() {
    local port=$1
    local pid_file=".claude-mpm/monitor-daemon-${port}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p $pid > /dev/null 2>&1; then
            echo "  Cleaning up daemon on port $port (PID: $pid)"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
            sleep 1
        fi
        rm -f "$pid_file"
    fi
    rm -f ".claude-mpm/monitor-daemon-${port}.log"
}

# Test function
test_daemon_start() {
    local test_num=$1
    local port=$2

    echo -e "${YELLOW}Test $test_num/$TOTAL_TESTS: Starting daemon on port $port${NC}"

    # Start daemon
    local output=$($PYTHON -m claude_mpm.cli monitor start --background --port $port 2>&1)
    local exit_code=$?

    if [ $exit_code -ne 0 ]; then
        echo -e "${RED}✗ FAIL: Daemon start command failed with exit code $exit_code${NC}"
        echo "  Output: $output"
        ((FAIL_COUNT++))
        return 1
    fi

    # Wait a moment for daemon to initialize
    sleep 2

    # Check if PID file exists
    local pid_file=".claude-mpm/monitor-daemon-${port}.pid"
    if [ ! -f "$pid_file" ]; then
        echo -e "${RED}✗ FAIL: PID file not created${NC}"
        ((FAIL_COUNT++))
        return 1
    fi

    local pid=$(cat "$pid_file")

    # Check if process is running
    if ! ps -p $pid > /dev/null 2>&1; then
        echo -e "${RED}✗ FAIL: Process $pid not running${NC}"
        ((FAIL_COUNT++))
        return 1
    fi

    # Check if port is bound
    if ! lsof -i :$port | grep LISTEN > /dev/null 2>&1; then
        echo -e "${RED}✗ FAIL: Port $port not bound${NC}"
        ((FAIL_COUNT++))
        cleanup_daemon $port
        return 1
    fi

    # Health check
    local health_check=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health 2>/dev/null || echo "000")
    if [ "$health_check" != "200" ]; then
        echo -e "${YELLOW}⚠ WARNING: Health check returned $health_check (may still be initializing)${NC}"
    fi

    echo -e "${GREEN}✓ SUCCESS: Daemon started (PID: $pid, Port: $port)${NC}"
    ((SUCCESS_COUNT++))

    # Cleanup
    cleanup_daemon $port

    return 0
}

# Clean up any existing daemons
echo "Cleaning up any existing daemons..."
for port in $(seq 8765 8790); do
    cleanup_daemon $port
done
echo ""

# Run tests
for i in $(seq 1 $TOTAL_TESTS); do
    # Alternate between different ports
    port=$((8765 + (i % 5)))
    test_daemon_start $i $port
    echo ""
done

# Summary
echo "======================================"
echo "Test Summary"
echo "======================================"
echo -e "Total Tests:    $TOTAL_TESTS"
echo -e "${GREEN}Successes:      $SUCCESS_COUNT${NC}"
echo -e "${RED}Failures:       $FAIL_COUNT${NC}"
echo -e "Success Rate:   $(echo "scale=1; $SUCCESS_COUNT * 100 / $TOTAL_TESTS" | bc)%"
echo ""

if [ $FAIL_COUNT -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    exit 1
fi
