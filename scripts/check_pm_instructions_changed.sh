#!/bin/bash
# Check if PM instruction files changed and run behavioral tests
#
# This script is designed to be run in CI/CD or pre-release checks.
# It detects changes to PM instruction source files and runs behavioral
# compliance tests if changes are found.
#
# Exit codes:
#   0 - No PM changes detected OR tests passed
#   1 - PM changes detected AND tests failed

set -e

echo "============================================================================="
echo "PM Instructions Change Detection"
echo "============================================================================="

# Define PM instruction source files
PM_INSTRUCTION_FILES=(
    "src/claude_mpm/agents/PM_INSTRUCTIONS.md"
    "src/claude_mpm/agents/WORKFLOW.md"
    "src/claude_mpm/agents/MEMORY.md"
    "src/claude_mpm/agents/templates/circuit-breakers.md"
)

# Check if any PM instruction files changed in last commit
echo "Checking for PM instruction changes in last commit..."

CHANGED_FILES=$(git diff --name-only HEAD~1 HEAD 2>/dev/null || echo "")

if [ -z "$CHANGED_FILES" ]; then
    echo "⚠️  No git history available (fresh repo or first commit)"
    echo "Skipping behavioral tests."
    exit 0
fi

# Check if any PM files were modified
PM_CHANGED=false
for file in "${PM_INSTRUCTION_FILES[@]}"; do
    if echo "$CHANGED_FILES" | grep -q "^${file}$"; then
        PM_CHANGED=true
        echo "  ✅ Changed: $file"
    fi
done

if [ "$PM_CHANGED" = false ]; then
    echo "✅ No PM instruction changes detected."
    echo "Skipping PM behavioral compliance tests."
    exit 0
fi

echo ""
echo "⚠️  PM instruction files changed!"
echo "Running PM behavioral compliance tests..."
echo "============================================================================="
echo ""

# Determine test severity based on environment
if [ "$CI" = "true" ] || [ "$RELEASE_CHECK" = "true" ]; then
    # In CI or release: run critical tests only (faster)
    SEVERITY="critical"
    echo "🔍 CI/Release mode: Running CRITICAL tests only"
else
    # Local development: run all tests
    SEVERITY="all"
    echo "🔍 Development mode: Running ALL tests"
fi

echo ""

# Run behavioral tests in release-check mode
python tests/eval/run_pm_behavioral_tests.py \
    --release-check \
    --severity "$SEVERITY" \
    --report

EXIT_CODE=$?

echo ""
echo "============================================================================="

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ PM behavioral compliance tests PASSED"
    echo ""
    echo "All PM behavioral requirements verified:"
    echo "  - Delegation-first principle"
    echo "  - Tool usage compliance"
    echo "  - Circuit breaker compliance"
    echo "  - Workflow sequence adherence"
    echo "  - Evidence-based assertions"
    echo "  - File tracking protocol"
    echo "  - Memory management"
    echo ""
    echo "Safe to release PM instruction changes."
else
    echo "❌ PM behavioral compliance tests FAILED"
    echo ""
    echo "PM instruction changes have introduced behavioral violations."
    echo ""
    echo "Review test output above and fix violations before releasing."
    echo ""
    echo "Common fixes:"
    echo "  1. Review PM_INSTRUCTIONS.md for contradictory rules"
    echo "  2. Check circuit breaker definitions in templates/circuit-breakers.md"
    echo "  3. Verify workflow sequence in WORKFLOW.md"
    echo "  4. Ensure all behavioral requirements are consistent"
    echo ""
    echo "Detailed report available at: tests/eval/reports/pm_behavioral_summary.md"
fi

echo "============================================================================="

exit $EXIT_CODE
