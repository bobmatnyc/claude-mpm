#!/bin/bash
# Test that claude-mpm creates .claude-mpm directory on startup

set -e

echo "Testing .claude-mpm directory creation on startup..."
echo "================================================="

# Create a test directory
TEST_DIR="/tmp/claude_mpm_test_$$"
mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "📍 Working in: $TEST_DIR"

# Remove any existing .claude-mpm directory
rm -rf .claude-mpm

echo "🚀 Running claude-mpm to check directory creation..."

# Run claude-mpm with a simple command that exits quickly
python -m claude_mpm info >/dev/null 2>&1 || true

echo ""
echo "📁 Checking if .claude-mpm was created..."

if [ -d ".claude-mpm" ]; then
    echo "✅ .claude-mpm directory exists!"
    
    # Check subdirectories
    echo ""
    echo "📂 Directory structure:"
    find .claude-mpm -type d | sort | sed 's/^/  /'
    
    # Specifically check for responses directory
    if [ -d ".claude-mpm/responses" ]; then
        echo ""
        echo "✅ responses/ directory exists (bug fix verified)"
    else
        echo ""
        echo "❌ responses/ directory is missing!"
        exit 1
    fi
else
    echo "❌ .claude-mpm directory was NOT created!"
    exit 1
fi

# Clean up
cd /
rm -rf "$TEST_DIR"

echo ""
echo "✅ All checks passed!"