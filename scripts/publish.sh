#!/bin/bash

# Script to publish both PyPI and npm packages

set -e

echo "🚀 Publishing claude-mpm packages..."

# Check if we're on a clean working directory
if [[ -n $(git status -s) ]]; then
    echo "❌ Working directory is not clean. Please commit changes first."
    exit 1
fi

# Get version from Python package
VERSION=$(python -c "import sys; sys.path.insert(0, 'src'); from claude_mpm._version import __version__; print(__version__)")
echo "📦 Version: $VERSION"

# Update npm package version to match
echo "📝 Updating npm package version..."
npm version $VERSION --no-git-tag-version --allow-same-version

# Build Python distribution
echo "🐍 Building Python distribution..."
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel

# Publish to PyPI
echo "📤 Publishing to PyPI..."
echo "Run: twine upload dist/*"
echo "(Requires PyPI credentials)"

# Publish to npm
echo "📤 Publishing to npm..."
echo "Run: npm publish"
echo "(Requires npm login)"

echo ""
echo "✅ Build complete! To publish:"
echo "1. PyPI: twine upload dist/*"
echo "2. npm: npm publish"