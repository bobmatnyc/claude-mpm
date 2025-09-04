#!/bin/bash
#
# Test script for JSON sticky state functionality
# Opens the test page in the default browser

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found"
    exit 1
fi

echo "Starting test server for JSON sticky state..."
echo "Test page will open at: http://localhost:8888/tests/dashboard/test_json_sticky_state.html"
echo ""
echo "Instructions:"
echo "1. Click 'Simulate New Event' to create test events"
echo "2. Toggle the 'Full Event Data' sections - they should all toggle together"
echo "3. Reload the page - the state should persist"
echo "4. Click 'Check LocalStorage' to verify persistence"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start a simple HTTP server
cd "$PROJECT_ROOT"
python3 -m http.server 8888 --bind localhost
