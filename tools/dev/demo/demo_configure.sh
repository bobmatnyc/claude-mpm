#!/bin/bash
# Demo script for the claude-mpm configure command

echo "====================================="
echo "Claude MPM Configure Command Demo"
echo "====================================="
echo

echo "1. Display help information:"
echo "   claude-mpm configure --help"
echo

echo "2. List all available agents:"
echo "   claude-mpm configure --list-agents"
claude-mpm configure --list-agents 2>/dev/null | head -20
echo

echo "3. Enable a specific agent:"
echo "   claude-mpm configure --enable-agent engineer"
claude-mpm configure --enable-agent engineer 2>/dev/null
echo

echo "4. Disable a specific agent:"
echo "   claude-mpm configure --disable-agent designer"
claude-mpm configure --disable-agent designer 2>/dev/null
echo

echo "5. Show version information:"
echo "   claude-mpm configure --version-info"
claude-mpm configure --version-info 2>/dev/null
echo

echo "6. Export configuration:"
echo "   claude-mpm configure --export-config my_config.json"
claude-mpm configure --export-config demo_config.json 2>/dev/null
echo "   Configuration exported to demo_config.json"
echo

echo "7. Interactive TUI (main menu):"
echo "   claude-mpm configure"
echo "   (This would launch the interactive interface)"
echo

echo "8. Jump directly to agent management:"
echo "   claude-mpm configure --agents"
echo "   (This would open agent management directly)"
echo

echo "9. User-level configuration:"
echo "   claude-mpm configure --scope user"
echo "   (This would manage user-level settings)"
echo

echo "====================================="
echo "Demo complete!"
echo "====================================="

# Clean up demo file
rm -f demo_config.json
