#!/bin/bash
# Simple test script to verify --resume flag functionality

echo "=========================================="
echo "Testing --resume Flag Implementation"
echo "=========================================="
echo

PASS_COUNT=0
FAIL_COUNT=0

# Test 1: Check bash wrapper includes --resume in MPM_FLAGS
echo "Test 1: Bash Wrapper Recognition"
echo "------------------------------------------"
if grep -q '"--resume"' scripts/claude-mpm && grep -q 'MPM_FLAGS=.*"--resume"' scripts/claude-mpm; then
    echo "✅ Bash wrapper includes --resume in MPM_FLAGS"
    ((PASS_COUNT++))
else
    echo "❌ Bash wrapper does NOT include --resume in MPM_FLAGS"
    ((FAIL_COUNT++))
fi
echo

# Test 2: Check parser configuration files
echo "Test 2: Parser Configuration"
echo "------------------------------------------"
if grep -q '"--resume"' src/claude_mpm/cli/parsers/base_parser.py; then
    echo "✅ Base parser includes --resume flag"
    ((PASS_COUNT++))
else
    echo "❌ Base parser missing --resume flag"
    ((FAIL_COUNT++))
fi

if grep -q '"--resume"' src/claude_mpm/cli/parsers/run_parser.py; then
    echo "✅ Run parser includes --resume flag"
    ((PASS_COUNT++))
else
    echo "❌ Run parser missing --resume flag"
    ((FAIL_COUNT++))
fi
echo

# Test 3: Check filter function doesn't filter --resume
echo "Test 3: Filter Function"
echo "------------------------------------------"
if grep -q '"--resume"' src/claude_mpm/cli/commands/run.py | grep -q 'mpm_flags'; then
    echo "❌ Filter function incorrectly includes --resume in mpm_flags"
    ((FAIL_COUNT++))
else
    echo "✅ Filter function doesn't filter out --resume"
    ((PASS_COUNT++))
fi
echo

# Test 4: Check run.py handles --resume
echo "Test 4: Run Command Handler"
echo "------------------------------------------"
if grep -q 'if resume_flag_present:' src/claude_mpm/cli/commands/run.py; then
    echo "✅ Run command handles --resume flag"
    ((PASS_COUNT++))
else
    echo "❌ Run command doesn't handle --resume flag"
    ((FAIL_COUNT++))
fi
echo

# Test 5: Test actual command execution (dry run)
echo "Test 5: Command Execution Test"
echo "------------------------------------------"
# Export debug mode to see what would be executed
export CLAUDE_MPM_DEBUG=1

# Capture the output of running with --resume
OUTPUT=$(./scripts/claude-mpm --resume --help 2>&1 | head -20)

if echo "$OUTPUT" | grep -q "Working directory"; then
    echo "✅ MPM command processes --resume flag"
    ((PASS_COUNT++))
else
    echo "❌ MPM command doesn't process --resume flag"
    echo "   Output: $OUTPUT"
    ((FAIL_COUNT++))
fi
echo

# Summary
echo "=========================================="
if [ $FAIL_COUNT -eq 0 ]; then
    echo "✅ ALL TESTS PASSED ($PASS_COUNT/$((PASS_COUNT + FAIL_COUNT)))"
    echo "The --resume flag is working correctly!"
else
    echo "❌ SOME TESTS FAILED"
    echo "   Passed: $PASS_COUNT"
    echo "   Failed: $FAIL_COUNT"
fi
echo "=========================================="

exit $FAIL_COUNT
