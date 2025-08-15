#!/bin/bash
#
# Install git pre-commit hook for automatic build number tracking
#
# WHY: Simplifies the installation of the build tracking system by automatically
# setting up the git pre-commit hook that increments build numbers.
#
# DESIGN DECISION: Provides both install and uninstall functionality, with
# backup of existing hooks to prevent data loss. Interactive prompts ensure
# user awareness of changes being made.
#
# Usage:
#   ./scripts/install_git_hook.sh          # Install the hook
#   ./scripts/install_git_hook.sh --remove # Remove the hook

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."

# Paths
HOOK_SOURCE="$SCRIPT_DIR/pre-commit-build.sh"
HOOK_DEST="$PROJECT_ROOT/.git/hooks/pre-commit"
HOOK_BACKUP="$PROJECT_ROOT/.git/hooks/pre-commit.backup"

# Check if we're in a git repository
if [ ! -d "$PROJECT_ROOT/.git" ]; then
    echo -e "${RED}Error: Not in a git repository${NC}" >&2
    echo "Please run this script from the claude-mpm project root" >&2
    exit 1
fi

# Check if hook source exists
if [ ! -f "$HOOK_SOURCE" ]; then
    echo -e "${RED}Error: Hook source not found at $HOOK_SOURCE${NC}" >&2
    exit 1
fi

# Function to install the hook
install_hook() {
    echo "Installing git pre-commit hook for build tracking..."
    
    # Check if a pre-commit hook already exists
    if [ -f "$HOOK_DEST" ]; then
        echo -e "${YELLOW}Warning: A pre-commit hook already exists${NC}"
        
        # Check if it's our hook
        if grep -q "claude-mpm build tracking" "$HOOK_DEST" 2>/dev/null; then
            echo "The existing hook appears to be our build tracking hook"
            read -p "Do you want to reinstall it? (y/n) " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                echo "Installation cancelled"
                exit 0
            fi
        else
            echo "The existing hook appears to be a custom hook"
            echo "Options:"
            echo "  1. Backup existing hook and install build tracking"
            echo "  2. Cancel installation"
            read -p "Choose option (1/2): " -n 1 -r
            echo
            
            if [[ $REPLY == "1" ]]; then
                # Backup existing hook
                echo "Backing up existing hook to $HOOK_BACKUP"
                cp "$HOOK_DEST" "$HOOK_BACKUP"
                echo -e "${GREEN}Backup created successfully${NC}"
            else
                echo "Installation cancelled"
                exit 0
            fi
        fi
    fi
    
    # Create hooks directory if it doesn't exist
    mkdir -p "$(dirname "$HOOK_DEST")"
    
    # Copy the hook
    cp "$HOOK_SOURCE" "$HOOK_DEST"
    chmod +x "$HOOK_DEST"
    
    echo -e "${GREEN}✓ Git pre-commit hook installed successfully${NC}"
    echo
    echo "The build tracking system is now active!"
    echo "Build numbers will automatically increment when you commit code changes."
    echo
    echo "Current build number: $(cat "$PROJECT_ROOT/BUILD_NUMBER" 2>/dev/null || echo "1")"
    echo
    echo "To test the hook manually:"
    echo "  python3 scripts/increment_build.py --check-only"
    echo
    echo "To remove the hook:"
    echo "  $0 --remove"
}

# Function to remove the hook
remove_hook() {
    echo "Removing git pre-commit hook..."
    
    if [ ! -f "$HOOK_DEST" ]; then
        echo "No pre-commit hook found"
        return 0
    fi
    
    # Check if it's our hook
    if grep -q "claude-mpm build tracking" "$HOOK_DEST" 2>/dev/null; then
        rm "$HOOK_DEST"
        echo -e "${GREEN}✓ Build tracking hook removed${NC}"
        
        # Check if there's a backup to restore
        if [ -f "$HOOK_BACKUP" ]; then
            read -p "A backup hook was found. Restore it? (y/n) " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                mv "$HOOK_BACKUP" "$HOOK_DEST"
                chmod +x "$HOOK_DEST"
                echo -e "${GREEN}✓ Backup hook restored${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}Warning: The existing hook doesn't appear to be our build tracking hook${NC}"
        read -p "Remove it anyway? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm "$HOOK_DEST"
            echo -e "${GREEN}✓ Hook removed${NC}"
        else
            echo "Removal cancelled"
        fi
    fi
}

# Main script logic
if [ "$1" == "--remove" ] || [ "$1" == "-r" ]; then
    remove_hook
elif [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Install or remove the git pre-commit hook for build tracking"
    echo
    echo "Options:"
    echo "  --remove, -r    Remove the installed hook"
    echo "  --help, -h      Show this help message"
    echo
    echo "Without options, the script will install the hook"
else
    install_hook
fi