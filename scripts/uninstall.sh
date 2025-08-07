#!/bin/bash
# Uninstallation script for claude-mpm

set -e

echo "🗑️  Uninstalling claude-mpm..."

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Remove symlinks
remove_symlinks() {
    if [ -L "$HOME/.local/bin/claude-mpm" ]; then
        rm "$HOME/.local/bin/claude-mpm"
        echo -e "${GREEN}✓ Removed claude-mpm symlink${NC}"
    fi
    
    if [ -L "$HOME/.local/bin/ticket" ]; then
        rm "$HOME/.local/bin/ticket"
        echo -e "${GREEN}✓ Removed ticket symlink${NC}"
    fi
}

# Ask about user data
remove_user_data() {
    echo
    echo -e "${YELLOW}User data found at ~/.claude-mpm${NC}"
    read -p "Remove user configuration and logs? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$HOME/.claude-mpm"
        echo -e "${GREEN}✓ Removed user data${NC}"
    else
        echo "User data preserved at ~/.claude-mpm"
    fi
}

# Remove from pip
uninstall_pip() {
    if pip show claude-mpm &> /dev/null; then
        pip uninstall -y claude-mpm
        echo -e "${GREEN}✓ Uninstalled from pip${NC}"
    fi
}

# Main uninstall
main() {
    echo "===================================="
    echo "Claude MPM Uninstallation"
    echo "===================================="
    echo
    
    # Remove components
    remove_symlinks
    uninstall_pip
    
    # Check for user data
    if [ -d "$HOME/.claude-mpm" ]; then
        remove_user_data
    fi
    
    echo
    echo -e "${GREEN}✨ Uninstallation complete!${NC}"
    echo
    echo "Project directory remains unchanged."
    echo "You can remove it manually if desired."
}

# Run main
main "$@"