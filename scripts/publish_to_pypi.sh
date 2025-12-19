#!/bin/bash
set -e  # Exit on error

# Script: Automated PyPI Publishing
# Description: Publishes Claude MPM to PyPI using credentials from ~/.pypirc

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function: Print colored message
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_message "$BLUE" "========================================"
print_message "$BLUE" "  Claude MPM - PyPI Publishing Script"
print_message "$BLUE" "========================================"
echo ""

# 1. Check we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    print_message "$RED" "Error: Must run from project root directory"
    print_message "$YELLOW" "Current directory: $(pwd)"
    exit 1
fi
print_message "$GREEN" "✓ Running from project root"

# 2. Verify ~/.pypirc exists
if [ ! -f "$HOME/.pypirc" ]; then
    print_message "$RED" "Error: ~/.pypirc file not found"
    print_message "$YELLOW" "Please create ~/.pypirc with PyPI credentials"
    print_message "$YELLOW" "See: https://packaging.python.org/en/latest/specifications/pypirc/"
    exit 1
fi

print_message "$GREEN" "✓ Found ~/.pypirc configuration"

# 4. Get version from VERSION file
if [ ! -f "VERSION" ]; then
    print_message "$RED" "Error: VERSION file not found"
    exit 1
fi

VERSION=$(cat VERSION | tr -d '[:space:]')
print_message "$YELLOW" "Publishing version: $VERSION"

# 5. Verify distribution files exist
WHEEL_FILE="dist/claude_mpm-${VERSION}-py3-none-any.whl"
TAR_FILE="dist/claude_mpm-${VERSION}.tar.gz"

if [ ! -f "$WHEEL_FILE" ]; then
    print_message "$RED" "Error: Wheel file not found: $WHEEL_FILE"
    print_message "$YELLOW" "Please run 'make safe-release-build' first"
    exit 1
fi

if [ ! -f "$TAR_FILE" ]; then
    print_message "$RED" "Error: Tar file not found: $TAR_FILE"
    print_message "$YELLOW" "Please run 'make safe-release-build' first"
    exit 1
fi

print_message "$GREEN" "✓ Found wheel: $WHEEL_FILE"
print_message "$GREEN" "✓ Found tarball: $TAR_FILE"

# Show file sizes
WHEEL_SIZE=$(ls -lh "$WHEEL_FILE" | awk '{print $5}')
TAR_SIZE=$(ls -lh "$TAR_FILE" | awk '{print $5}')
print_message "$BLUE" "  Wheel size: $WHEEL_SIZE"
print_message "$BLUE" "  Tarball size: $TAR_SIZE"

# 6. Verify uv is available
if ! command -v uv &> /dev/null; then
    print_message "$RED" "Error: uv not found"
    print_message "$YELLOW" "Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
else
    print_message "$GREEN" "✓ uv is available"
fi

# 7. Confirmation prompt
echo ""
print_message "$YELLOW" "Ready to upload to PyPI:"
print_message "$BLUE" "  Package: claude-mpm"
print_message "$BLUE" "  Version: $VERSION"
print_message "$BLUE" "  Files: 2 (wheel + tarball)"
echo ""
read -p "Continue with upload? [y/N]: " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_message "$YELLOW" "Upload cancelled by user"
    exit 0
fi

# 8. Upload to PyPI
echo ""
print_message "$YELLOW" "Uploading to PyPI..."
print_message "$BLUE" "This may take a moment..."
echo ""

# Use uv publish with credentials from ~/.pypirc
# UV will automatically read the [pypi] section from ~/.pypirc
if uv publish "$WHEEL_FILE" "$TAR_FILE"; then

    echo ""
    print_message "$GREEN" "========================================"
    print_message "$GREEN" "  ✓ Successfully published to PyPI!"
    print_message "$GREEN" "========================================"
    echo ""
    print_message "$GREEN" "Package available at:"
    print_message "$BLUE" "  https://pypi.org/project/claude-mpm/$VERSION/"
    echo ""
    print_message "$YELLOW" "Test installation with:"
    print_message "$BLUE" "  pip install --upgrade claude-mpm"
    print_message "$BLUE" "  pip install claude-mpm==$VERSION"
    echo ""
else
    echo ""
    print_message "$RED" "========================================"
    print_message "$RED" "  ✗ Upload failed"
    print_message "$RED" "========================================"
    echo ""
    print_message "$YELLOW" "Common issues:"
    print_message "$YELLOW" "  • Invalid API token"
    print_message "$YELLOW" "  • Version already exists on PyPI"
    print_message "$YELLOW" "  • Network connectivity issues"
    print_message "$YELLOW" "  • Package name conflicts"
    echo ""
    exit 1
fi
