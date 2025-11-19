#!/usr/bin/env bash
# Test script to verify claude-mpm wrapper script startup behavior

echo "=== Testing claude-mpm wrapper script startup behavior ==="
echo ""

echo "Test 1: Default startup (should be SILENT - no wrapper messages)"
echo "Command: ./scripts/claude-mpm --version"
echo "Expected: Only version number, no [INFO] messages"
echo "---"
./scripts/claude-mpm --version 2>&1 | head -5
echo ""
echo ""

echo "Test 2: Startup with --debug flag (should show verbose messages)"
echo "Command: ./scripts/claude-mpm --debug --version"
echo "Expected: [INFO] messages about debug mode, working directory, etc."
echo "---"
./scripts/claude-mpm --debug --version 2>&1 | head -10
echo ""
echo ""

echo "Test 3: Startup with --verbose flag (should show verbose messages)"
echo "Command: ./scripts/claude-mpm --verbose --version"
echo "Expected: [INFO] messages about working directory, framework path"
echo "---"
./scripts/claude-mpm --verbose --version 2>&1 | head -10
echo ""
echo ""

echo "Test 4: Startup with -d flag (shorthand for debug)"
echo "Command: ./scripts/claude-mpm -d --version"
echo "Expected: [INFO] messages similar to --debug"
echo "---"
./scripts/claude-mpm -d --version 2>&1 | head -10
echo ""
echo ""

echo "Test 5: Regular MPM command (should be silent)"
echo "Command: ./scripts/claude-mpm --help"
echo "Expected: Clean output without wrapper messages"
echo "---"
./scripts/claude-mpm --help 2>&1 | head -5
echo ""
echo ""

echo "=== All tests complete ==="
echo ""
echo "Summary:"
echo "✅ Test 1: Default startup should show NO [INFO] messages"
echo "✅ Test 2: --debug flag should show verbose [INFO] messages"
echo "✅ Test 3: --verbose flag should show verbose [INFO] messages"
echo "✅ Test 4: -d flag should show verbose [INFO] messages"
echo "✅ Test 5: Regular commands should be clean"
