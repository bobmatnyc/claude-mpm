#!/bin/bash
# Run all tests for claude-mpm

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Running Claude MPM Tests ==="
echo "Project root: $PROJECT_ROOT"
echo

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Create test directory if it doesn't exist
TEST_DIR="$HOME/Tests/claude-mpm-test"
mkdir -p "$TEST_DIR"

echo "1. Running unit tests..."
cd "$PROJECT_ROOT" && python3 "$SCRIPT_DIR/tests/run_tests_updated.py"

echo
echo "2. Running hello world test..."
cd "$TEST_DIR" && python3 "$SCRIPT_DIR/tests/test_hello_world.py"

echo
echo "3. Running agent integration test..."
python3 "$SCRIPT_DIR/tests/test_agent_integration.py"

echo
echo "=== All tests complete ==="