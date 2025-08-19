#!/usr/bin/env bash
# Claude Code hook wrapper for claude-mpm

# Debug log (optional - comment out in production)
echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Wrapper called with args: $@" >> /tmp/hook-wrapper.log

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Detect if we're in a development environment or installed package
if [ -d "$SCRIPT_DIR/../../../../venv" ]; then
    # Development environment - script is in src/claude_mpm/hooks/claude_hooks/
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../.." && pwd )"
    PYTHON_CMD="python"

    # Activate the virtual environment if it exists
    if [ -f "$PROJECT_ROOT/venv/bin/activate" ]; then
        source "$PROJECT_ROOT/venv/bin/activate"
    fi

    # Set PYTHONPATH for development
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
else
    # Installed package - use system Python and installed claude_mpm
    PYTHON_CMD="python3"

    # Try to detect if we're in a virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        PYTHON_CMD="$VIRTUAL_ENV/bin/python"
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    fi
fi

# Check if we should use DEBUG logging
if [[ " $* " =~ " --logging DEBUG " ]] || [[ " $* " =~ " --debug " ]]; then
    export CLAUDE_MPM_LOG_LEVEL="DEBUG"
fi

# Set Socket.IO configuration for hook events
export CLAUDE_MPM_SOCKETIO_PORT="8765"
export CLAUDE_MPM_HOOK_DEBUG="true"

# Debug log (optional)
echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] PYTHONPATH: $PYTHONPATH" >> /tmp/hook-wrapper.log
echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Running: $PYTHON_CMD -m claude_mpm.hooks.claude_hooks.hook_handler" >> /tmp/hook-wrapper.log
echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] SOCKETIO_PORT: $CLAUDE_MPM_SOCKETIO_PORT" >> /tmp/hook-wrapper.log

# Run the Python hook handler as a module with error handling
# Use exec to replace the shell process, but wrap in error handling
if ! "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/hook-error.log; then
    # If the Python handler fails, always return continue to not block Claude
    echo '{"action": "continue"}'
    # Log the error for debugging
    echo "[$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)] Hook handler failed, see /tmp/hook-error.log" >> /tmp/hook-wrapper.log
    exit 0
fi

# Success - Python handler already printed continue, just exit
exit 0
