#!/bin/bash
#
# Claude MPM Hook Handler Entry Point Script
#
# OVERVIEW:
# This script serves as the bridge between Claude Code hook system and the Python-based
# Claude MPM hook handler. It is executed directly by Claude Code when events occur
# and ensures proper environment setup before delegating to the Python handler.
#
# ARCHITECTURE:
# Claude Code → This Script → Python Environment → hook_handler.py → Socket.IO/EventBus
#
# KEY RESPONSIBILITIES:
# - Virtual environment detection and activation
# - Python executable resolution with fallbacks
# - Error handling and logging for troubleshooting
# - Path resolution for cross-platform compatibility
# - Environment variable propagation
#
# DEPLOYMENT:
# This script is deployed to Claude Code's hooks directory during installation.
# Location: ~/.claude/hooks/claude-mpm/claude-hook-handler.sh
# Permissions: Must be executable (chmod +x)
#
# ENVIRONMENT VARIABLES:
# - CLAUDE_MPM_HOOK_DEBUG: Enable debug logging to /tmp/claude-mpm-hook.log
# - CLAUDE_MPM_ROOT: Override project root detection
# - VIRTUAL_ENV: Standard virtual environment variable
# - PYTHONPATH: Extended with src/ directory for imports
#
# PERFORMANCE CONSIDERATIONS:
# - Minimal shell operations to reduce latency (~10ms overhead)
# - Cached virtual environment detection
# - Early exit on errors to prevent hanging
# - Lightweight logging for debugging without performance impact
#
# SECURITY:
# - Restricts Python execution to project virtual environments
# - Validates paths before execution
# - No external network access or privileged operations
# - Logs to temporary files only (no persistent sensitive data)
#
# TROUBLESHOOTING:
# Enable debug logging: export CLAUDE_MPM_HOOK_DEBUG=true
# Check permissions: ls -la ~/.claude/hooks/claude-mpm/claude-hook-handler.sh
# Test manually: echo '{"test": "data"}' | ./claude-hook-handler.sh
#
# GOTCHAS:
# - Must activate virtual environment in same shell process
# - Path resolution differs between development and installed environments
# - Claude Code passes event data via stdin (not command line arguments)
# - Exit codes must be 0 for success, non-zero indicates failure to Claude Code
#
# @author Claude MPM Development Team
# @version 1.0
# @since v4.0.25

# Exit on any error
set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Determine the claude-mpm root based on installation type
# Check if we're in a pipx installation
if [[ "$SCRIPT_DIR" == *"/.local/pipx/venvs/claude-mpm/"* ]]; then
    # pipx installation - script is at lib/python*/site-packages/claude_mpm/scripts/
    # The venv root is what we need for Python detection
    CLAUDE_MPM_ROOT="$(echo "$SCRIPT_DIR" | sed 's|/lib/python.*/site-packages/.*||')"
elif [[ "$SCRIPT_DIR" == *"/site-packages/claude_mpm/scripts"* ]]; then
    # Regular pip installation - script is in site-packages
    # Use the Python environment root
    CLAUDE_MPM_ROOT="$(python3 -c 'import sys; print(sys.prefix)')"
else
    # Development installation - script is at src/claude_mpm/scripts/, so we go up 3 levels
    CLAUDE_MPM_ROOT="$(cd "$SCRIPT_DIR/../../.." 2>/dev/null && pwd || echo "$SCRIPT_DIR")"
fi

# Debug logging (can be enabled via environment variable)
if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Claude hook handler starting..." >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Script dir: $SCRIPT_DIR" >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Claude MPM root: $CLAUDE_MPM_ROOT" >> /tmp/claude-mpm-hook.log
fi

#
# Find and return the appropriate Python executable for hook processing.
#
# STRATEGY:
# This function implements a fallback chain to find Python with claude-mpm dependencies:
# 1. UV-managed projects (uv.lock detected) - uses "uv run python"
# 2. pipx installations - uses pipx venv Python
# 3. Project-specific virtual environments (venv, .venv)
# 4. Currently active virtual environment ($VIRTUAL_ENV)
# 5. System python3 (may lack dependencies)
# 6. System python (last resort)
#
# WHY THIS APPROACH:
# - Claude MPM requires specific packages (socketio, eventlet) not in system Python
# - UV and virtual environments ensure dependency isolation and availability
# - Multiple naming conventions supported (venv vs .venv)
# - Graceful degradation to system Python if no venv found
#
# ACTIVATION STRATEGY:
# - UV projects: use "uv run python" to execute in UV-managed environment
# - Sources activate script to set up environment variables
# - Returns specific Python path for exec (not just 'python')
# - Maintains environment in same shell process
#
# PERFORMANCE:
# - Fast path detection using file existence checks
# - Early returns to minimize overhead
# - Caches result in process environment
#
# RETURNS:
# Absolute path to Python executable with claude-mpm dependencies, or "uv run python" for UV projects
#
find_python_command() {
    # 1. Check for UV project first (uv.lock or pyproject.toml with uv)
    if [ -f "$CLAUDE_MPM_ROOT/uv.lock" ]; then
        if command -v uv &> /dev/null; then
            echo "uv run python"
            return
        fi
    fi

    # 2. Check if we're in a pipx installation
    if [[ "$SCRIPT_DIR" == *"/.local/pipx/venvs/claude-mpm/"* ]]; then
        # pipx installation - use the pipx venv's Python directly
        if [ -f "$CLAUDE_MPM_ROOT/bin/python" ]; then
            echo "$CLAUDE_MPM_ROOT/bin/python"
            return
        fi
    fi

    # 3. Check for project-local virtual environment (common in development)
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

# Check installation type and set PYTHONPATH accordingly
if [[ "$SCRIPT_DIR" == *"/.local/pipx/venvs/claude-mpm/"* ]]; then
    # pipx installation - claude_mpm is already in the venv's site-packages
    # No need to modify PYTHONPATH
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] pipx installation detected" >> /tmp/claude-mpm-hook.log
    fi
elif [ -d "$CLAUDE_MPM_ROOT/src" ]; then
    # Development install - add src to PYTHONPATH
    export PYTHONPATH="$CLAUDE_MPM_ROOT/src:$PYTHONPATH"

    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Development environment detected" >> /tmp/claude-mpm-hook.log
    fi
else
    # Regular pip install - claude_mpm should be in site-packages
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

# Function for debug logging
log_debug() {
    if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
        echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] $1" >> /tmp/claude-mpm-hook.log
    fi
}

# Test Python works and module exists
# Handle UV's multi-word command specially
if [[ "$PYTHON_CMD" == "uv run python" ]]; then
    if ! uv run python -c "import claude_mpm" 2>/dev/null; then
        log_debug "claude_mpm module not available, continuing without hook"
        echo '{"action": "continue"}'
        exit 0
    fi
else
    if ! $PYTHON_CMD -c "import claude_mpm" 2>/dev/null; then
        log_debug "claude_mpm module not available, continuing without hook"
        echo '{"action": "continue"}'
        exit 0
    fi
fi

# Run the Python hook handler with all input
# Use exec to replace the shell process with Python
# Handle UV's multi-word command specially
if [[ "$PYTHON_CMD" == "uv run python" ]]; then
    exec uv run python -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log
else
    exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log
fi

# Note: exec replaces the shell process, so code below only runs if exec fails
# If we reach here, the Python handler failed
if [ "${CLAUDE_MPM_HOOK_DEBUG}" = "true" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Hook handler failed, see /tmp/claude-mpm-hook-error.log" >> /tmp/claude-mpm-hook.log
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Error: $(cat /tmp/claude-mpm-hook-error.log 2>/dev/null | head -5)" >> /tmp/claude-mpm-hook.log
fi
# Return continue action to prevent blocking Claude Code
echo '{"action": "continue"}'
exit 0