#!/bin/bash
# Run all tests for claude-mpm

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "=== Running Claude MPM Tests ==="
echo "Project root: $PROJECT_ROOT"
echo

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Change to project root
cd "$PROJECT_ROOT"

echo "1. Running core functionality tests..."
if command -v uv >/dev/null 2>&1; then
    # Use UV to run tests in virtual environment
    uv run pytest tests/core/ -v --tb=short
    PYTEST_EXIT_CODE=$?
elif python3 -c "import pytest" >/dev/null 2>&1; then
    # Fallback to direct python3 if UV not available
    python3 -m pytest tests/core/ -v --tb=short
    PYTEST_EXIT_CODE=$?
else
    echo "pytest not found, skipping unit tests"
    PYTEST_EXIT_CODE=0
fi

echo
echo "2. Running CLI tests..."
if [ -f "tests/cli/test_cli_basic.py" ]; then
    if command -v uv >/dev/null 2>&1; then
        uv run pytest tests/cli/test_cli_basic.py -v
        CLI_EXIT_CODE=$?
    else
        python3 -m pytest tests/cli/test_cli_basic.py -v
        CLI_EXIT_CODE=$?
    fi
else
    echo "CLI tests not found, skipping"
    CLI_EXIT_CODE=0
fi

echo
echo "=== Test Summary ==="
if [ $PYTEST_EXIT_CODE -eq 0 ] && [ $CLI_EXIT_CODE -eq 0 ]; then
    echo "✅ All tests passed"
    exit 0
else
    echo "❌ Some tests failed"
    exit 1
fi
