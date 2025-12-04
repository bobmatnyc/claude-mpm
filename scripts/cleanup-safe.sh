#!/bin/bash
# cleanup-safe.sh - Remove files that can be safely regenerated
# Part of Claude MPM Framework cleanup utilities

set -e  # Exit on error

echo "🧹 Claude MPM Framework - Safe Cleanup Script"
echo "================================================"
echo ""

# Function to report space saved
report_space() {
    local dir=$1
    if [ -d "$dir" ]; then
        du -sh "$dir" 2>/dev/null || echo "0B"
    else
        echo "0B (already removed)"
    fi
}

# Track total space saved
total_saved=0

# 1. Remove build artifacts
echo "📦 Removing build artifacts..."
SIZE_DIST=$(du -sk ./dist 2>/dev/null | cut -f1 || echo "0")
SIZE_BUILD=$(du -sk ./build 2>/dev/null | cut -f1 || echo "0")
SIZE_EGG=$(du -sk ./src/claude_mpm.egg-info 2>/dev/null | cut -f1 || echo "0")

rm -rf ./dist/
rm -rf ./build/
rm -rf ./src/claude_mpm.egg-info/
rm -rf ./tools/build/

total_saved=$((total_saved + SIZE_DIST + SIZE_BUILD + SIZE_EGG))
echo "✅ Build artifacts removed: $((SIZE_DIST + SIZE_BUILD + SIZE_EGG)) KB"

# 2. Remove test artifacts
echo "🧪 Removing test artifacts..."
SIZE_PYTEST=$(du -sk ./.pytest_cache 2>/dev/null | cut -f1 || echo "0")
SIZE_HTMLCOV=$(du -sk ./htmlcov 2>/dev/null | cut -f1 || echo "0")
SIZE_COVERAGE=$(du -sk ./.coverage 2>/dev/null | cut -f1 || echo "0")

rm -rf ./.pytest_cache/
rm -rf ./htmlcov/
rm -f ./.coverage
rm -f ./coverage.xml

total_saved=$((total_saved + SIZE_PYTEST + SIZE_HTMLCOV + SIZE_COVERAGE))
echo "✅ Test artifacts removed: $((SIZE_PYTEST + SIZE_HTMLCOV + SIZE_COVERAGE)) KB"

# 3. Remove __pycache__ directories
echo "🐍 Removing Python bytecode..."
PYCACHE_COUNT=$(find . -type d -name "__pycache__" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" 2>/dev/null | wc -l)

find . -type d -name "__pycache__" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -exec rm -rf {} + 2>/dev/null || true

find . -name "*.pyc" -o -name "*.pyo" -o -name "*.pyd" \
  -not -path "./venv/*" \
  -not -path "./node_modules/*" \
  -not -path "./.venv/*" \
  -delete 2>/dev/null || true

echo "✅ Removed $PYCACHE_COUNT __pycache__ directories"

# 4. Remove system temp files
echo "🗑️  Removing system temp files..."
DS_STORE_COUNT=$(find . -name ".DS_Store" 2>/dev/null | wc -l)
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true
find . -name "*.swp" -o -name "*.swo" -delete 2>/dev/null || true

echo "✅ Removed $DS_STORE_COUNT .DS_Store files"

# Summary
echo ""
echo "================================================"
echo "✨ Safe cleanup complete!"
echo "📊 Approximate space saved: $((total_saved / 1024)) MB"
echo ""
echo "⚠️  Note: Virtual environments (venv/) were not removed"
echo "   To remove venv/ and rebuild:"
echo "   $ rm -rf ./venv/ ./.venv/"
echo "   $ python3 -m venv venv"
echo "   $ source venv/bin/activate"
echo "   $ pip install -e '.[dev]'"
echo ""
