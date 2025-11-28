#!/usr/bin/env bash
# Script to identify which test file causes the test suite to hang
# Usage: ./scripts/identify_hung_test.sh

set -euo pipefail

TIMEOUT=15
RESULTS_FILE="test_hang_results.txt"

echo "Testing individual test files to identify hangs..."
echo "Timeout per file: ${TIMEOUT}s"
echo ""
echo "Results will be saved to: $RESULTS_FILE"
echo ""

# Clear previous results
> "$RESULTS_FILE"

# Find all test files
test_files=$(find tests -name "test_*.py" -o -name "*_test.py" | sort)

total=$(echo "$test_files" | wc -l | tr -d ' ')
current=0

for test_file in $test_files; do
    current=$((current + 1))
    echo -n "[$current/$total] Testing $test_file... "

    # Run with timeout
    if timeout ${TIMEOUT}s pytest "$test_file" -v --tb=short > /dev/null 2>&1; then
        echo "✓ PASSED"
        echo "PASSED: $test_file" >> "$RESULTS_FILE"
    else
        exit_code=$?
        if [ $exit_code -eq 124 ]; then
            echo "✗ HUNG (timeout after ${TIMEOUT}s)"
            echo "HUNG: $test_file" >> "$RESULTS_FILE"
        else
            echo "✗ FAILED (exit code: $exit_code)"
            echo "FAILED: $test_file (exit: $exit_code)" >> "$RESULTS_FILE"
        fi
    fi
done

echo ""
echo "==============================================="
echo "Summary:"
echo "==============================================="
echo ""
echo "Hung tests:"
grep "^HUNG:" "$RESULTS_FILE" || echo "  None found"
echo ""
echo "Failed tests:"
grep "^FAILED:" "$RESULTS_FILE" || echo "  None found"
echo ""
echo "Full results saved to: $RESULTS_FILE"
