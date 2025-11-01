#!/bin/bash
# Script to verify PyPI publishing setup without actually publishing
# Safe to run - performs read-only checks only

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

echo ""
print_message "$BLUE" "========================================="
print_message "$BLUE" "  PyPI Publishing Setup Verification"
print_message "$BLUE" "========================================="
echo ""

ERRORS=0
WARNINGS=0

# 1. Check project root
print_message "$YELLOW" "Checking project structure..."
if [ ! -f "pyproject.toml" ]; then
    print_message "$RED" "✗ Not in project root (pyproject.toml not found)"
    ERRORS=$((ERRORS + 1))
else
    print_message "$GREEN" "✓ Running from project root"
fi

# 2. Check .env.local exists
if [ ! -f ".env.local" ]; then
    print_message "$RED" "✗ .env.local file not found"
    print_message "$YELLOW" "  Create it with: echo 'PYPI_API_KEY=pypi-...' > .env.local"
    ERRORS=$((ERRORS + 1))
else
    print_message "$GREEN" "✓ .env.local file exists"

    # Check file permissions
    PERMS=$(stat -f "%A" .env.local 2>/dev/null || stat -c "%a" .env.local 2>/dev/null)
    if [ "$PERMS" = "600" ]; then
        print_message "$GREEN" "✓ .env.local has secure permissions (600)"
    else
        print_message "$YELLOW" "⚠ .env.local permissions: $PERMS (recommended: 600)"
        print_message "$YELLOW" "  Run: chmod 600 .env.local"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 3. Check .gitignore
echo ""
print_message "$YELLOW" "Checking git configuration..."
if git check-ignore -q .env.local 2>/dev/null; then
    print_message "$GREEN" "✓ .env.local is gitignored"
else
    print_message "$RED" "✗ .env.local is NOT gitignored"
    print_message "$YELLOW" "  Add to .gitignore: echo '.env.local' >> .gitignore"
    ERRORS=$((ERRORS + 1))
fi

# Check if .env.local would be committed
if git ls-files --error-unmatch .env.local 2>/dev/null; then
    print_message "$RED" "✗ .env.local is tracked by git!"
    print_message "$YELLOW" "  Remove with: git rm --cached .env.local"
    ERRORS=$((ERRORS + 1))
else
    print_message "$GREEN" "✓ .env.local is not tracked by git"
fi

# 4. Check API key (without exposing it)
echo ""
print_message "$YELLOW" "Checking API key..."
if [ -f ".env.local" ]; then
    source .env.local

    if [ -z "$PYPI_API_KEY" ]; then
        print_message "$RED" "✗ PYPI_API_KEY not set in .env.local"
        ERRORS=$((ERRORS + 1))
    else
        KEY_LENGTH=${#PYPI_API_KEY}
        print_message "$GREEN" "✓ PYPI_API_KEY is set ($KEY_LENGTH characters)"

        # Check format
        if [[ "$PYPI_API_KEY" =~ ^pypi- ]]; then
            print_message "$GREEN" "✓ API key has correct format (starts with 'pypi-')"
        else
            print_message "$YELLOW" "⚠ API key doesn't start with 'pypi-'"
            print_message "$YELLOW" "  This might not be a valid PyPI API token"
            WARNINGS=$((WARNINGS + 1))
        fi

        # Check length (typical PyPI tokens are 200+ chars)
        if [ "$KEY_LENGTH" -lt 100 ]; then
            print_message "$YELLOW" "⚠ API key seems short ($KEY_LENGTH chars)"
            print_message "$YELLOW" "  PyPI tokens are typically 200+ characters"
            WARNINGS=$((WARNINGS + 1))
        fi
    fi
fi

# 5. Check VERSION file
echo ""
print_message "$YELLOW" "Checking version information..."
if [ ! -f "VERSION" ]; then
    print_message "$RED" "✗ VERSION file not found"
    ERRORS=$((ERRORS + 1))
else
    VERSION=$(cat VERSION | tr -d '[:space:]')
    print_message "$GREEN" "✓ VERSION file exists: $VERSION"
fi

# 6. Check distribution files
echo ""
print_message "$YELLOW" "Checking distribution files..."
if [ ! -d "dist" ]; then
    print_message "$YELLOW" "⚠ dist/ directory not found"
    print_message "$YELLOW" "  Run 'make safe-release-build' to create distribution files"
    WARNINGS=$((WARNINGS + 1))
else
    WHEEL_COUNT=$(ls dist/*.whl 2>/dev/null | wc -l)
    TAR_COUNT=$(ls dist/*.tar.gz 2>/dev/null | wc -l)

    if [ "$WHEEL_COUNT" -eq 0 ] || [ "$TAR_COUNT" -eq 0 ]; then
        print_message "$YELLOW" "⚠ No distribution files in dist/"
        print_message "$YELLOW" "  Run 'make safe-release-build' to build packages"
        WARNINGS=$((WARNINGS + 1))
    else
        print_message "$GREEN" "✓ Found $WHEEL_COUNT wheel file(s)"
        print_message "$GREEN" "✓ Found $TAR_COUNT tarball(s)"

        if [ -f "VERSION" ]; then
            VERSION=$(cat VERSION | tr -d '[:space:]')
            WHEEL_FILE="dist/claude_mpm-${VERSION}-py3-none-any.whl"
            TAR_FILE="dist/claude_mpm-${VERSION}.tar.gz"

            if [ -f "$WHEEL_FILE" ] && [ -f "$TAR_FILE" ]; then
                WHEEL_SIZE=$(ls -lh "$WHEEL_FILE" | awk '{print $5}')
                TAR_SIZE=$(ls -lh "$TAR_FILE" | awk '{print $5}')
                print_message "$GREEN" "✓ Distribution files for v$VERSION ready:"
                print_message "$BLUE" "  Wheel: $WHEEL_SIZE"
                print_message "$BLUE" "  Tarball: $TAR_SIZE"
            else
                print_message "$YELLOW" "⚠ Distribution files don't match VERSION ($VERSION)"
                print_message "$YELLOW" "  Run 'make safe-release-build' to rebuild"
                WARNINGS=$((WARNINGS + 1))
            fi
        fi
    fi
fi

# 7. Check required tools
echo ""
print_message "$YELLOW" "Checking required tools..."

if command -v twine &> /dev/null; then
    TWINE_VERSION=$(twine --version | head -n1)
    print_message "$GREEN" "✓ twine is installed: $TWINE_VERSION"
else
    print_message "$YELLOW" "⚠ twine not installed (will be auto-installed if needed)"
    print_message "$YELLOW" "  Install with: pip install twine"
    WARNINGS=$((WARNINGS + 1))
fi

if command -v git &> /dev/null; then
    print_message "$GREEN" "✓ git is installed"
else
    print_message "$RED" "✗ git not installed"
    ERRORS=$((ERRORS + 1))
fi

if command -v python &> /dev/null || command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python --version 2>&1 || python3 --version 2>&1)
    print_message "$GREEN" "✓ Python is installed: $PYTHON_VERSION"
else
    print_message "$RED" "✗ Python not installed"
    ERRORS=$((ERRORS + 1))
fi

# 8. Check publish script
echo ""
print_message "$YELLOW" "Checking publish script..."
if [ ! -f "scripts/publish_to_pypi.sh" ]; then
    print_message "$RED" "✗ Publish script not found"
    ERRORS=$((ERRORS + 1))
else
    print_message "$GREEN" "✓ Publish script exists"

    if [ -x "scripts/publish_to_pypi.sh" ]; then
        print_message "$GREEN" "✓ Publish script is executable"
    else
        print_message "$YELLOW" "⚠ Publish script not executable"
        print_message "$YELLOW" "  Run: chmod +x scripts/publish_to_pypi.sh"
        WARNINGS=$((WARNINGS + 1))
    fi
fi

# 9. Summary
echo ""
print_message "$BLUE" "========================================="
print_message "$BLUE" "  Verification Summary"
print_message "$BLUE" "========================================="
echo ""

if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    print_message "$GREEN" "✅ All checks passed! Ready to publish."
    echo ""
    print_message "$BLUE" "To publish to PyPI, run:"
    print_message "$YELLOW" "  make publish-pypi"
    print_message "$YELLOW" "  # or"
    print_message "$YELLOW" "  ./scripts/publish_to_pypi.sh"
    echo ""
    exit 0
elif [ $ERRORS -eq 0 ]; then
    print_message "$YELLOW" "⚠️  Setup complete with $WARNINGS warning(s)"
    print_message "$YELLOW" "You can publish, but consider fixing warnings first."
    echo ""
    exit 0
else
    print_message "$RED" "❌ Found $ERRORS error(s) and $WARNINGS warning(s)"
    print_message "$RED" "Please fix the errors before publishing."
    echo ""
    exit 1
fi
