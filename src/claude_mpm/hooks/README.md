# Claude Code Hooks System

This directory contains the Claude Code hook integration for claude-mpm.

## Overview

The hook system allows claude-mpm to intercept and handle commands typed in Claude Code, particularly the `/mpm` commands.

## Version Requirements

**Claude Code 1.0.92 or higher is required for hook monitoring features.**

Earlier versions of Claude Code do not support the matcher-based hook configuration format needed for real-time event monitoring. If you have an older version:
- The dashboard and other features will still work
- Real-time monitoring will not be available
- You'll see a clear message about the version requirement
- To enable monitoring, upgrade Claude Code to 1.0.92+

**Claude Code 2.0.30 or higher is required for PreToolUse input modification.**

This advanced feature allows hooks to modify tool inputs before execution, enabling:
- Context injection into file operations
- Security guards that validate and block dangerous operations
- Parameter enhancement with default values
- Logging and auditing of tool invocations

See [PreToolUse Hook Documentation](../../docs/developer/pretool-use-hooks.md) for details.

## Architecture (v4.1.8+)

Claude MPM uses a **deployment-root hook architecture** where Claude Code directly calls a script within the claude-mpm installation. See [HOOK_ARCHITECTURE.md](../../docs/developer/HOOK_ARCHITECTURE.md) for details.

## Structure

```
hooks/
├── claude_hooks/                      # Claude Code hook implementation
│   ├── hook_handler.py               # Main Python handler that processes events
│   ├── installer.py                  # Hook installation and configuration
│   ├── event_handlers.py             # Event processing logic
│   ├── memory_integration.py         # Memory system integration
│   ├── response_tracking.py          # Response tracking
│   └── services/                     # Service modules
│       ├── connection_manager.py     # SocketIO/HTTP connections
│       ├── state_manager.py          # State and delegation tracking
│       └── subagent_processor.py     # Subagent response processing
├── templates/                         # Hook script templates
│   ├── pre_tool_use_template.py      # Comprehensive PreToolUse template
│   ├── pre_tool_use_simple.py        # Simple PreToolUse template
│   └── README.md                     # Template documentation
└── scripts/
    └── claude-hook-handler.sh        # Deployment-root hook script (called by Claude Code)
```

## Claude Code Hooks

The Claude Code hooks are the primary integration point between claude-mpm and Claude Code. They allow:

- Intercepting `/mpm` commands before they reach the LLM
- Providing custom responses and actions
- Blocking LLM processing when appropriate

### Installation

To install the Claude Code hooks:

```bash
# Using the configure command (recommended)
claude-mpm configure --install-hooks

# Or check your version compatibility first
claude-mpm configure --verify-hooks
```

This will:
1. Check your Claude Code version for compatibility
2. If compatible (1.0.92+), create/update `~/.claude/settings.json` with hook configuration
3. Install the smart hook script that dynamically finds claude-mpm
4. Copy any custom commands to `~/.claude/commands/`

If your Claude Code version is older than 1.0.92:
- You'll see a message explaining the version requirement
- Hooks will not be installed to prevent configuration errors
- The system will continue to work without real-time monitoring

### How It Works

1. When you type in Claude Code, it triggers hook events
2. Claude Code calls `hook_wrapper.sh` (the path in `~/.claude/settings.json`)
3. The wrapper script:
   - Detects if it's running from a local dev environment, npm, or PyPI installation
   - Activates the appropriate Python environment
   - Runs `hook_handler.py` with the event data
4. The handler processes various event types:
   - **UserPromptSubmit**: Checks if the prompt starts with `/mpm` and handles commands
   - **PreToolUse**: Logs tool usage before execution
   - **PostToolUse**: Logs tool results after execution
   - **Stop**: Logs when a session or task stops
   - **SubagentStop**: Logs when a subagent completes with agent type and ID
5. For `/mpm` commands, it returns exit code 2 to block LLM processing
6. All events are logged to project-specific log files in `.claude-mpm/logs/`

### Available Commands

- `/mpm` - Show help and available commands
- `/mpm status` - Show claude-mpm status and environment
- `/mpm help` - Show detailed help

### Debugging

To enable debug logging for hooks:

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
```

Then run Claude Code from that terminal. Hook events will be logged to `~/.claude-mpm/logs/`.

## Legacy Hook System (Removed)

The `builtin/` directory that contained the old internal hook system has been removed. All hook functionality is now handled through the Claude Code hooks system.

## Development

To add new `/mpm` commands:

1. Edit `hook_handler.py` to handle the new command
2. Update the help text in the `handle_mpm_help()` function
3. Test by running Claude Code with the new command

## Exit Codes

The hook system uses specific exit codes:

- `0` - Success, continue normal processing
- `2` - Block LLM processing (command was handled)
- Other - Error occurred

## Environment Variables

- `CLAUDE_MPM_LOG_LEVEL` - Set to DEBUG for detailed logging
- `HOOK_EVENT_TYPE` - Set by Claude Code (UserPromptSubmit, PreToolUse, PostToolUse)
- `HOOK_DATA` - JSON data from Claude Code with event details