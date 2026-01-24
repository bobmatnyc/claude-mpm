#!/bin/bash
set -e  # Exit on error

# Script: Automated NPM Publishing
# Description: Publishes package to NPM using credentials from environment, ~/.npmrc, or .env.local

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

# Function: Show help
show_help() {
    echo ""
    print_message "$BLUE" "NPM Publishing Script"
    echo ""
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message and exit"
    echo "  -y, --yes      Skip confirmation prompt"
    echo "  --dry-run      Run npm publish with --dry-run flag"
    echo ""
    echo "Description:"
    echo "  Publishes the current package to NPM registry."
    echo "  Looks for NPM_TOKEN in the following order:"
    echo "    1. NPM_TOKEN environment variable"
    echo "    2. Existing ~/.npmrc with auth token"
    echo "    3. .env.local file with NPM_TOKEN=..."
    echo ""
    echo "Examples:"
    echo "  $(basename "$0")           # Interactive publish"
    echo "  $(basename "$0") --yes     # Non-interactive publish"
    echo "  $(basename "$0") --dry-run # Test without publishing"
    echo ""
    exit 0
}

# Parse arguments
SKIP_CONFIRM=false
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            ;;
        -y|--yes)
            SKIP_CONFIRM=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            print_message "$RED" "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

print_message "$BLUE" "========================================"
print_message "$BLUE" "  NPM Publishing Script"
print_message "$BLUE" "========================================"
echo ""

# 1. Check we're in the right directory (package.json exists)
if [ ! -f "package.json" ]; then
    print_message "$RED" "Error: package.json not found"
    print_message "$YELLOW" "Current directory: $(pwd)"
    print_message "$YELLOW" "Please run from a directory containing package.json"
    exit 1
fi
print_message "$GREEN" "✓ Found package.json"

# 2. Extract package info
PACKAGE_NAME=$(node -p "require('./package.json').name" 2>/dev/null || echo "unknown")
PACKAGE_VERSION=$(node -p "require('./package.json').version" 2>/dev/null || echo "unknown")

if [ "$PACKAGE_NAME" = "unknown" ] || [ "$PACKAGE_VERSION" = "unknown" ]; then
    print_message "$RED" "Error: Could not read package name/version from package.json"
    exit 1
fi

print_message "$BLUE" "  Package: $PACKAGE_NAME"
print_message "$BLUE" "  Version: $PACKAGE_VERSION"
echo ""

# 3. Check for NPM token
TOKEN_SOURCE=""
NPM_AUTH_TOKEN=""

# Check environment variable first
if [ -n "$NPM_TOKEN" ]; then
    NPM_AUTH_TOKEN="$NPM_TOKEN"
    TOKEN_SOURCE="environment variable"
    print_message "$GREEN" "✓ Found NPM_TOKEN in environment"
fi

# Check ~/.npmrc if no token yet
if [ -z "$NPM_AUTH_TOKEN" ] && [ -f "$HOME/.npmrc" ]; then
    EXISTING_TOKEN=$(grep '//registry.npmjs.org/:_authToken=' "$HOME/.npmrc" 2>/dev/null | cut -d'=' -f2 | head -1)
    if [ -n "$EXISTING_TOKEN" ]; then
        NPM_AUTH_TOKEN="$EXISTING_TOKEN"
        TOKEN_SOURCE="~/.npmrc"
        print_message "$GREEN" "✓ Found auth token in ~/.npmrc"
    fi
fi

# Check .env.local if no token yet
if [ -z "$NPM_AUTH_TOKEN" ] && [ -f ".env.local" ]; then
    ENV_TOKEN=$(grep '^NPM_TOKEN=' ".env.local" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'" | head -1)
    if [ -n "$ENV_TOKEN" ]; then
        NPM_AUTH_TOKEN="$ENV_TOKEN"
        TOKEN_SOURCE=".env.local"
        print_message "$GREEN" "✓ Found NPM_TOKEN in .env.local"
    fi
fi

# Exit if no token found
if [ -z "$NPM_AUTH_TOKEN" ]; then
    print_message "$RED" "Error: No NPM authentication token found"
    echo ""
    print_message "$YELLOW" "Please provide NPM_TOKEN via one of:"
    print_message "$YELLOW" "  1. Environment variable: export NPM_TOKEN=npm_xxxxx"
    print_message "$YELLOW" "  2. ~/.npmrc file with: //registry.npmjs.org/:_authToken=npm_xxxxx"
    print_message "$YELLOW" "  3. .env.local file with: NPM_TOKEN=npm_xxxxx"
    echo ""
    print_message "$YELLOW" "Get your token from: https://www.npmjs.com/settings/~/tokens"
    exit 1
fi

# 4. Write token to ~/.npmrc if not already there
NPMRC_HAS_TOKEN=false
if [ -f "$HOME/.npmrc" ]; then
    if grep -q '//registry.npmjs.org/:_authToken=' "$HOME/.npmrc" 2>/dev/null; then
        NPMRC_HAS_TOKEN=true
    fi
fi

if [ "$NPMRC_HAS_TOKEN" = false ]; then
    print_message "$YELLOW" "Writing auth token to ~/.npmrc..."

    # Backup existing .npmrc if it exists
    if [ -f "$HOME/.npmrc" ]; then
        cp "$HOME/.npmrc" "$HOME/.npmrc.backup"
        print_message "$BLUE" "  Backed up existing ~/.npmrc to ~/.npmrc.backup"
    fi

    # Append token to .npmrc
    echo "//registry.npmjs.org/:_authToken=${NPM_AUTH_TOKEN}" >> "$HOME/.npmrc"
    print_message "$GREEN" "✓ Auth token written to ~/.npmrc"
else
    print_message "$GREEN" "✓ ~/.npmrc already configured with auth token"
fi

# 5. Verify npm is available
if ! command -v npm &> /dev/null; then
    print_message "$RED" "Error: npm not found"
    print_message "$YELLOW" "Please install Node.js and npm"
    exit 1
fi
print_message "$GREEN" "✓ npm is available ($(npm --version))"

# 6. Check if version already exists on npm
print_message "$YELLOW" "Checking if version exists on NPM..."
if npm view "${PACKAGE_NAME}@${PACKAGE_VERSION}" version &>/dev/null; then
    print_message "$RED" "Error: Version ${PACKAGE_VERSION} already exists on NPM"
    print_message "$YELLOW" "Please bump the version in package.json before publishing"
    exit 1
fi
print_message "$GREEN" "✓ Version ${PACKAGE_VERSION} is available"

# 7. Confirmation prompt
echo ""
print_message "$YELLOW" "Ready to publish to NPM:"
print_message "$BLUE" "  Package: $PACKAGE_NAME"
print_message "$BLUE" "  Version: $PACKAGE_VERSION"
print_message "$BLUE" "  Token source: $TOKEN_SOURCE"
if [ "$DRY_RUN" = true ]; then
    print_message "$BLUE" "  Mode: DRY RUN (no actual publish)"
fi
echo ""

if [ "$SKIP_CONFIRM" = false ]; then
    read -p "Continue with upload? [y/N]: " -n 1 -r
    echo ""

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_message "$YELLOW" "Upload cancelled by user"
        exit 0
    fi
fi

# 8. Publish to NPM
echo ""
print_message "$YELLOW" "Publishing to NPM..."
print_message "$BLUE" "This may take a moment..."
echo ""

PUBLISH_CMD="npm publish"
if [ "$DRY_RUN" = true ]; then
    PUBLISH_CMD="npm publish --dry-run"
fi

if $PUBLISH_CMD; then
    echo ""
    print_message "$GREEN" "========================================"
    if [ "$DRY_RUN" = true ]; then
        print_message "$GREEN" "  ✓ Dry run completed successfully!"
    else
        print_message "$GREEN" "  ✓ Successfully published to NPM!"
    fi
    print_message "$GREEN" "========================================"
    echo ""
    if [ "$DRY_RUN" = false ]; then
        print_message "$GREEN" "Package available at:"
        print_message "$BLUE" "  https://www.npmjs.com/package/${PACKAGE_NAME}/v/${PACKAGE_VERSION}"
        echo ""
        print_message "$YELLOW" "Install with:"
        print_message "$BLUE" "  npm install ${PACKAGE_NAME}"
        print_message "$BLUE" "  npm install ${PACKAGE_NAME}@${PACKAGE_VERSION}"
        echo ""
    fi
else
    echo ""
    print_message "$RED" "========================================"
    print_message "$RED" "  ✗ Publish failed"
    print_message "$RED" "========================================"
    echo ""
    print_message "$YELLOW" "Common issues:"
    print_message "$YELLOW" "  • Invalid or expired auth token"
    print_message "$YELLOW" "  • Version already exists on NPM"
    print_message "$YELLOW" "  • Package name conflicts or is taken"
    print_message "$YELLOW" "  • Network connectivity issues"
    print_message "$YELLOW" "  • Missing publish permissions"
    echo ""
    exit 1
fi
