#!/bin/bash
# cleanup-review.sh - Remove files that should be reviewed first
# Part of Claude MPM Framework cleanup utilities

set -e

echo "🔍 Claude MPM Framework - Cleanup with Review"
echo "=============================================="
echo ""

# Function to ask for confirmation
confirm() {
    local prompt="$1"
    read -p "$prompt [y/N] " -n 1 -r
    echo
    [[ $REPLY =~ ^[Yy]$ ]]
}

# 1. Review and remove /tmp/ directory
if [ -d "./tmp" ]; then
    echo "📁 Found ./tmp/ directory (928 KB)"
    echo "   Contents: 35 markdown files, 8 Python files"

    # Check for docs/ subdirectory
    if [ -d "./tmp/docs" ]; then
        echo "⚠️  WARNING: ./tmp/docs/ subdirectory exists!"
        echo "   This may contain valuable research."

        if confirm "   View contents before removing?"; then
            ls -lh ./tmp/docs/
            echo ""
        fi

        if confirm "   Move ./tmp/docs/ to ./docs/research/?"; then
            mkdir -p ./docs/research/
            mv ./tmp/docs/* ./docs/research/ 2>/dev/null
            echo "   ✅ Moved to ./docs/research/"
        fi
    fi

    if confirm "🗑️  Remove ./tmp/ directory?"; then
        du -sh ./tmp/
        rm -rf ./tmp/
        echo "✅ ./tmp/ removed"
    else
        echo "⏭️  Skipped ./tmp/"
    fi
fi

# 2. Review and remove test logs
if confirm "🗑️  Remove old test log files?"; then
    rm -rf ./tests/test_logs/ 2>/dev/null
    rm -rf ./tests/artifacts/test_results/*.log 2>/dev/null
    rm -rf ./tests/integration/.claude-mpm/logs/ 2>/dev/null
    rm -rf ./tests/test-npm-install/.claude-mpm/logs/ 2>/dev/null
    echo "✅ Test logs removed"
else
    echo "⏭️  Skipped test logs"
fi

# 3. Review skipped test files
if [ -f "./tests/core/SKIP_test_framework_loader_unit.py" ]; then
    echo ""
    echo "📝 Found 4 skipped test files (97.8 KB total)"
    echo "   - tests/core/SKIP_test_framework_loader_unit.py (19 KB)"
    echo "   - tests/core/SKIP_test_framework_loader_comprehensive.py (40 KB)"
    echo "   - tests/cli/commands/SKIP_test_run_socketio_integration.py (9.8 KB)"
    echo "   - tests/SKIP_test_misc.py (29 KB)"
    echo ""

    if confirm "🗑️  Remove skipped test files?"; then
        rm ./tests/core/SKIP_test_framework_loader_unit.py 2>/dev/null
        rm ./tests/core/SKIP_test_framework_loader_comprehensive.py 2>/dev/null
        rm ./tests/cli/commands/SKIP_test_run_socketio_integration.py 2>/dev/null
        rm ./tests/SKIP_test_misc.py 2>/dev/null
        echo "✅ Skipped test files removed"
    else
        echo "⏭️  Skipped test files kept for review"
    fi
fi

echo ""
echo "================================================"
echo "✅ Review-based cleanup complete!"
echo ""
