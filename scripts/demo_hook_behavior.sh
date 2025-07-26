#!/bin/bash
# Demo script to show hook behavior

echo "=== Claude Code Hook Behavior Demo ==="
echo ""
echo "The claude-mpm hooks are installed in: ~/.claude/settings.json"
echo ""

# Check if hooks are installed
if [ -f ~/.claude/settings.json ]; then
    echo "✓ Claude Code hooks are installed"
    echo ""
    echo "Hook configuration:"
    cat ~/.claude/settings.json | python3 -m json.tool | grep -A5 -B2 "hook_wrapper.sh"
    echo ""
else
    echo "✗ Claude Code hooks not installed"
    echo "Run: python scripts/install_hooks.py"
    exit 1
fi

echo "=== Hook Behavior ==="
echo ""
echo "1. When you type /mpm in Claude Code:"
echo "   - Claude Code calls the hook_wrapper.sh script"
echo "   - The wrapper activates the Python environment"
echo "   - It runs hook_handler.py with the event data"
echo "   - The handler checks if the prompt starts with /mpm"
echo "   - If it does, it handles the command and exits with code 2"
echo "   - Exit code 2 tells Claude Code to block LLM processing"
echo ""
echo "2. Logging behavior:"
echo "   - Hooks use claude-mpm's logging system"
echo "   - When DEBUG is enabled, events are logged to ~/.claude-mpm/logs/"
echo "   - You can enable DEBUG by setting CLAUDE_MPM_LOG_LEVEL=DEBUG"
echo ""
echo "3. Available /mpm commands:"
echo "   - /mpm         : Show help and available commands"
echo "   - /mpm status  : Show claude-mpm status and environment"
echo "   - /mpm help    : Show detailed help"
echo ""
echo "=== Testing Hook Execution ==="
echo ""
echo "To test the hooks:"
echo "1. Open Claude Code"
echo "2. Type: /mpm status"
echo "3. The hook will intercept and display status (no LLM processing)"
echo ""
echo "To see debug logs:"
echo "1. Set environment: export CLAUDE_MPM_LOG_LEVEL=DEBUG"
echo "2. Run Claude Code from that terminal"
echo "3. Use /mpm commands"
echo "4. Check logs: tail -f ~/.claude-mpm/logs/latest.log"