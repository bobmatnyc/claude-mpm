#!/bin/bash
# Claude MPM Hook Handler Script
# This script is called directly by Claude Code hooks
# It sets up the proper Python environment and calls the Python hook handler

# Exit on any error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine the claude-mpm root
# The script is at src/claude_mpm/scripts/, so we go up 3 levels
CLAUDE_MPM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

# Debug logging (can be enabled via environment variable)
if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Claude hook handler starting..." >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Script dir: $SCRIPT_DIR" >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Claude MPM root: $CLAUDE_MPM_ROOT" >> /tmp/claude-mpm-hook.log
fi

# Function to find Python command
find_python_command() {
    # Check for virtual environment in the project
    if [ -f "$CLAUDE_MPM_ROOT/venv/bin/activate" ]; then
        source "$CLAUDE_MPM_ROOT/venv/bin/activate"
        echo "$CLAUDE_MPM_ROOT/venv/bin/python"
    elif [ -f "$CLAUDE_MPM_ROOT/.venv/bin/activate" ]; then
        source "$CLAUDE_MPM_ROOT/.venv/bin/activate"
        echo "$CLAUDE_MPM_ROOT/.venv/bin/python"
    elif [ -n "$VIRTUAL_ENV" ]; then
        # Already in a virtual environment
        echo "$VIRTUAL_ENV/bin/python"
    elif command -v python3 &> /dev/null; then
        echo "python3"
    else
        echo "python"
    fi
}

# Set up Python command
PYTHON_CMD=$(find_python_command)

# Check if we're in a development environment (has src directory)
if [ -d "$CLAUDE_MPM_ROOT/src" ]; then
    # Development install - add src to PYTHONPATH
    export PYTHONPATH="$CLAUDE_MPM_ROOT/src:$PYTHONPATH"
    
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Development environment detected" >> /tmp/claude-mpm-hook.log
    fi
else
    # Pip install - claude_mpm should be in site-packages
    # No need to modify PYTHONPATH
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Pip installation detected" >> /tmp/claude-mpm-hook.log
    fi
fi

# Debug logging
if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] PYTHON_CMD: $PYTHON_CMD" >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] PYTHONPATH: $PYTHONPATH" >> /tmp/claude-mpm-hook.log
fi

# Set Socket.IO configuration for hook events
export CLAUDE_MPM_SOCKETIO_PORT="${CLAUDE_MPM_SOCKETIO_PORT:-8765}"

# Run the Python hook handler with all input
# Use exec to replace the shell process with Python
if ! exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log; then
    # If the Python handler fails, always return continue to not block Claude
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Hook handler failed, see /tmp/claude-mpm-hook-error.log" >> /tmp/claude-mpm-hook.log
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Error: $(cat /tmp/claude-mpm-hook-error.log 2>/dev/null | head -5)" >> /tmp/claude-mpm-hook.log
    fi
    # Return continue action to prevent blocking Claude Code
    echo '{"action": "continue"}'
    exit 0
fi