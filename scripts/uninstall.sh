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

# Remove Claude Code hooks
remove_hooks() {
    echo "Removing Claude Code hooks..."

    # Try using the Python hook installer service if available
    if command -v python3 &> /dev/null; then
        python3 -c "
from claude_mpm.services.hook_installer_service import HookInstallerService
try:
    service = HookInstallerService()
    if service.uninstall_hooks():
        print('✓ Removed Claude Code hooks')
    else:
        print('⚠️  Could not remove Claude Code hooks')
except Exception as e:
    print(f'⚠️  Could not remove hooks: {e}')
" 2>/dev/null || {
            # Fallback: manually remove hooks from Claude settings
            if [ -f "$HOME/.claude/settings.json" ]; then
                echo "Attempting manual hook removal..."
                # Use Python to safely modify JSON
                python3 -c "
import json
import sys
from pathlib import Path

settings_file = Path.home() / '.claude' / 'settings.json'
if settings_file.exists():
    with open(settings_file, 'r') as f:
        settings = json.load(f)

    # Remove our hooks
    if 'hooks' in settings:
        hook_types = ['UserPromptSubmit', 'PreToolUse', 'PostToolUse', 'Stop', 'SubagentStop']
        for hook_type in hook_types:
            if hook_type in settings['hooks']:
                # Filter out our hooks (containing hook_wrapper.sh)
                filtered = []
                for cfg in settings['hooks'][hook_type]:
                    is_ours = False
                    if 'hooks' in cfg:
                        for h in cfg.get('hooks', []):
                            if 'hook_wrapper.sh' in h.get('command', ''):
                                is_ours = True
                                break
                    if not is_ours:
                        filtered.append(cfg)

                if filtered:
                    settings['hooks'][hook_type] = filtered
                else:
                    del settings['hooks'][hook_type]

        # Remove empty hooks section
        if 'hooks' in settings and not settings['hooks']:
            del settings['hooks']

    # Write back
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)

    print('✓ Removed Claude Code hooks manually')
" 2>/dev/null || echo -e "${YELLOW}⚠️  Could not remove Claude Code hooks${NC}"
            fi
        }
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
    remove_hooks
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
