#!/bin/bash
# Test script to capture Claude MPM startup logs

# Set log level to INFO for detailed output
export CLAUDE_MPM_LOG_LEVEL=INFO

# Capture both stdout and stderr
echo "=== Claude MPM Startup Test ==="
echo "Testing version: $(claude-mpm --version)"
echo ""
echo "=== Starting Claude MPM with doctor (should see banner + progress bars) ==="
echo ""

# Run with doctor command to trigger full startup sequence
# Note: doctor skips background services, so we use agents list instead
claude-mpm agents list 2>&1

echo ""
echo "=== Startup test complete ==="
