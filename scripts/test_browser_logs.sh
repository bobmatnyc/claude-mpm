#!/bin/bash

# Test script for verifying browser console log display
# This script tests that browser logs appear in the Browser Logs tab only

set -e

echo "=================================="
echo "Browser Console Log Display Test"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if monitor is running
echo "1. Checking if monitor server is running..."
if curl -s http://localhost:8765/api/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Monitor server is running on port 8765"
else
    echo -e "${YELLOW}!${NC} Monitor server not running. Starting it now..."
    ./scripts/claude-mpm monitor start &
    sleep 3
    if curl -s http://localhost:8765/api/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Monitor server started successfully"
    else
        echo -e "${RED}✗${NC} Failed to start monitor server"
        exit 1
    fi
fi

echo ""
echo "2. Opening test page and dashboard..."
echo "   Test page: file://${PWD}/test_browser_logs.html"
echo "   Dashboard: http://localhost:8765"
echo ""

# Open test page in browser
if [[ "$OSTYPE" == "darwin"* ]]; then
    open "file://${PWD}/test_browser_logs.html"
    open "http://localhost:8765"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open "file://${PWD}/test_browser_logs.html"
    xdg-open "http://localhost:8765"
else
    echo "Please manually open:"
    echo "  - file://${PWD}/test_browser_logs.html"
    echo "  - http://localhost:8765"
fi

echo ""
echo "3. Test Instructions:"
echo "   a) In Claude, run: /mpm-browser-monitor start"
echo "   b) In the dashboard, click on the 'Browser Logs' tab"
echo "   c) In the test page, click the test buttons"
echo "   d) Verify logs appear ONLY in Browser Logs tab"
echo ""
echo "Expected Results:"
echo "  ${GREEN}✓${NC} Browser Logs tab shows console.log, console.error, etc."
echo "  ${GREEN}✓${NC} Hook events (Start, Stop, ToolUse) appear in Events tab"
echo "  ${GREEN}✓${NC} No hook events appear in Browser Logs tab"
echo "  ${GREEN}✓${NC} Log entries show: timestamp, level, browser ID, message"
echo ""
echo "4. Testing via curl (simulating browser console log)..."

# Send a test browser console log via curl
BROWSER_ID="test-$(date +%s)"
TEST_RESPONSE=$(curl -s -X POST http://localhost:8765/api/browser-log \
    -H "Content-Type: application/json" \
    -d "{
        \"browser_id\": \"${BROWSER_ID}\",
        \"level\": \"INFO\",
        \"message\": \"Test console.log from curl at $(date)\",
        \"url\": \"http://test.example.com\",
        \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"
    }" \
    -w "\n%{http_code}")

HTTP_CODE=$(echo "$TEST_RESPONSE" | tail -n1)

if [ "$HTTP_CODE" == "204" ]; then
    echo -e "${GREEN}✓${NC} Successfully sent test browser log via API"
    echo "   Browser ID: ${BROWSER_ID}"
    echo "   Check the Browser Logs tab to see this test message"
else
    echo -e "${RED}✗${NC} Failed to send test browser log (HTTP $HTTP_CODE)"
fi

echo ""
echo "=================================="
echo "Test setup complete!"
echo "=================================="
echo ""
echo "Now follow the instructions above to complete the test."
echo "Press Ctrl+C to stop the monitor server when done."
echo ""

# Keep script running if we started the monitor
wait