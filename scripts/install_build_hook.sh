#!/bin/bash
#
# Install the build tracking git pre-commit hook for claude-mpm
#
# This script sets up automatic build number incrementing for code changes.
# Run this from the project root directory.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Find the project root
PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
}

echo "Setting up build tracking for claude-mpm..."
echo "Project root: $PROJECT_ROOT"

# Check if we're in the right project
if [ ! -f "$PROJECT_ROOT/scripts/increment_build.py" ]; then
    echo -e "${RED}Error: increment_build.py not found. Are you in the claude-mpm project?${NC}"
    exit 1
fi

# Git hooks directory
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

# Source and destination paths
SOURCE_HOOK="$PROJECT_ROOT/scripts/pre-commit-build.sh"
DEST_HOOK="$HOOKS_DIR/pre-commit"

# Create hooks directory if it doesn't exist
mkdir -p "$HOOKS_DIR"

# Check if a pre-commit hook already exists
if [ -f "$DEST_HOOK" ]; then
    echo -e "${YELLOW}Warning: A pre-commit hook already exists${NC}"
    echo "Current hook content (first 10 lines):"
    head -n 10 "$DEST_HOOK"
    echo ""
    read -p "Do you want to (r)eplace it, (b)ackup and replace, or (c)ancel? [r/b/c]: " choice
    
    case "$choice" in
        r|R)
            echo "Replacing existing hook..."
            ;;
        b|B)
            backup_name="$DEST_HOOK.backup.$(date +%Y%m%d_%H%M%S)"
            echo "Backing up existing hook to: $backup_name"
            cp "$DEST_HOOK" "$backup_name"
            ;;
        *)
            echo -e "${YELLOW}Installation cancelled${NC}"
            exit 0
            ;;
    esac
fi

# Copy the hook
cp "$SOURCE_HOOK" "$DEST_HOOK"
chmod +x "$DEST_HOOK"

echo -e "${GREEN}✓ Git pre-commit hook installed successfully${NC}"
echo ""
echo "The build tracking system is now active!"
echo ""
echo "How it works:"
echo "  • The build number will auto-increment when you commit code changes"
echo "  • Code changes are: *.py files in src/, *.sh files in scripts/"
echo "  • Documentation and config changes won't trigger a build increment"
echo "  • Current build number: $(cat "$PROJECT_ROOT/BUILD_VERSION" 2>/dev/null || echo "1")"
echo ""
echo "Manual operations:"
echo "  • Force increment: python3 scripts/increment_build.py --force"
echo "  • Check current build: cat BUILD_VERSION"
echo "  • Uninstall hook: rm .git/hooks/pre-commit"
echo ""
echo -e "${GREEN}Build tracking is ready to use!${NC}"