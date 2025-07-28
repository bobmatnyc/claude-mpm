#!/bin/bash

# Script to publish both PyPI and npm packages
#
# OPERATIONAL PURPOSE:
# Legacy build script for manual package distribution. Superseded by release.py
# which provides automated version management and synchronized releases.
# Kept for emergency manual releases and troubleshooting.
#
# DEPLOYMENT WORKFLOW:
# 1. Verifies clean git working directory
# 2. Extracts version from Python package
# 3. Synchronizes npm package.json version
# 4. Builds Python distribution packages
# 5. Provides manual upload commands
#
# OPERATIONAL NOTES:
# - This script builds but does NOT publish automatically
# - Manual upload commands prevent accidental releases
# - Use release.py for automated deployments
# - Useful for testing package builds without publishing
#
# PREREQUISITES:
# - Python build tools: pip install build twine
# - npm installed and configured
# - PyPI credentials in ~/.pypirc
# - npm credentials via npm login
#
# MONITORING:
# - Check dist/ directory for built packages
# - Verify package sizes are reasonable (200-300KB)
# - Ensure both .tar.gz and .whl files are created
# - Confirm package.json version matches VERSION file
#
# TROUBLESHOOTING:
# - Import error: Ensure src/ is in PYTHONPATH
# - Build fails: Check setup.py configuration
# - Version mismatch: Run manage_version.py first
# - npm error: Verify npm is installed and logged in

set -e  # Exit on any error - critical for deployment safety

echo "🚀 Publishing claude-mpm packages..."

# Check if we're on a clean working directory
# CRITICAL: Prevents accidental release of uncommitted changes
# Working directory must be clean to ensure reproducible builds
if [[ -n $(git status -s) ]]; then
    echo "❌ Working directory is not clean. Please commit changes first."
    exit 1
fi

# Get version from Python package
# OPERATIONAL NOTE: Extracts version from single source of truth
# Falls back gracefully if module structure changes
VERSION=$(python -c "import sys; sys.path.insert(0, 'src'); from claude_mpm._version import __version__; print(__version__)")
echo "📦 Version: $VERSION"

# Update npm package version to match
# SYNCHRONIZATION: Ensures PyPI and npm versions are identical
# --no-git-tag-version: Prevents duplicate git operations
# --allow-same-version: Enables re-runs without errors
echo "📝 Updating npm package version..."
npm version $VERSION --no-git-tag-version --allow-same-version

# Build Python distribution
# CLEANUP: Removes old build artifacts to prevent contamination
# sdist: Source distribution for pip install from source
# bdist_wheel: Binary wheel for faster installation
echo "🐍 Building Python distribution..."
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel

# Publish to PyPI
# MANUAL STEP: Requires explicit action to prevent accidents
# twine: Secure upload tool with credential management
# Verify package on test.pypi.org before production release
echo "📤 Publishing to PyPI..."
echo "Run: twine upload dist/*"
echo "(Requires PyPI credentials)"

# Publish to npm
# MANUAL STEP: Requires explicit npm publish command
# Publishes as @bobmatnyc/claude-mpm scoped package
# Check npm registry for successful publication
echo "📤 Publishing to npm..."
echo "Run: npm publish"
echo "(Requires npm login)"

echo ""
echo "✅ Build complete! To publish:"
echo "1. PyPI: twine upload dist/*"
echo "2. npm: npm publish"
echo ""
echo "POST-DEPLOYMENT VERIFICATION:"
echo "- PyPI: pip install claude-mpm==$VERSION"
echo "- npm: npm install @bobmatnyc/claude-mpm@$VERSION"
echo "- GitHub: Create release at https://github.com/BobMcNugget/claude-mpm/releases"