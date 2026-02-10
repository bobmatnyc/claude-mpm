#!/bin/bash

# Test runner for CLI commands
# WHY: Provides a quick way to test CLI command coverage and identify issues
# USAGE: ./scripts/test_cli_commands.sh [command_name]

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================="
echo "CLI Commands Test Runner"
echo "========================================="

# Function to run tests for a specific command
run_command_tests() {
    local command=$1
    local test_file="tests/cli/commands/test_${command}_command.py"

    if [ -f "$test_file" ]; then
        echo -e "\n${GREEN}Testing ${command} command...${NC}"
        python -m pytest "$test_file" -v --tb=short --no-header 2>&1 | grep -E "PASSED|FAILED|ERROR|test_" || true

        # Count results
        local passed=$(python -m pytest "$test_file" -q --tb=no 2>&1 | grep -c "passed" || echo "0")
        local failed=$(python -m pytest "$test_file" -q --tb=no 2>&1 | grep -c "failed" || echo "0")

        echo -e "${GREEN}✓ Passed: $passed${NC}"
        if [ "$failed" -gt 0 ]; then
            echo -e "${RED}✗ Failed: $failed${NC}"
        fi
    else
        echo -e "${YELLOW}⚠ No tests found for ${command} command${NC}"
    fi
}

# If specific command provided, test only that
if [ $# -eq 1 ]; then
    run_command_tests "$1"
    exit 0
fi

# Test all priority commands
echo -e "\n${YELLOW}Testing Priority Commands${NC}"
echo "========================================="

PRIORITY_COMMANDS=("run" "agents" "config")

for cmd in "${PRIORITY_COMMANDS[@]}"; do
    run_command_tests "$cmd"
    echo "-----------------------------------------"
done

# Test other commands if they exist
echo -e "\n${YELLOW}Testing Other Commands${NC}"
echo "========================================="

OTHER_COMMANDS=("monitor" "aggregate" "cleanup")

for cmd in "${OTHER_COMMANDS[@]}"; do
    run_command_tests "$cmd"
    echo "-----------------------------------------"
done

# Summary
echo -e "\n========================================="
echo -e "${GREEN}Test Summary${NC}"
echo "========================================="

# Run all tests with summary
python -m pytest tests/cli/commands/ --tb=no -q 2>&1 | tail -5

# Coverage report (if coverage is installed)
if command -v coverage &> /dev/null; then
    echo -e "\n${YELLOW}Generating coverage report...${NC}"
    coverage run -m pytest tests/cli/commands/ --tb=no -q > /dev/null 2>&1 || true
    coverage report --include="*/cli/commands/*" 2>/dev/null || echo "Coverage report generation failed"
fi

echo -e "\n${GREEN}Test run complete!${NC}"
echo "For detailed output, run: python -m pytest tests/cli/commands/ -v"
