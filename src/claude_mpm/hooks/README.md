# Claude Code Hooks System

This directory contains the Claude Code hook integration for claude-mpm.

## Overview

The hook system allows claude-mpm to intercept and handle commands typed in Claude Code, particularly the `/mpm` commands.

## Structure

```
hooks/
├── claude_hooks/              # Claude Code hook implementation
│   ├── hook_handler.py       # Main Python handler that processes events
│   └── hook_wrapper.sh       # Shell wrapper script (this is what gets installed in ~/.claude/settings.json)
└── builtin/                  # Legacy internal hooks (deprecated)
```

## Claude Code Hooks

The Claude Code hooks are the primary integration point between claude-mpm and Claude Code. They allow:

- Intercepting `/mpm` commands before they reach the LLM
- Providing custom responses and actions
- Blocking LLM processing when appropriate

### Installation

To install the Claude Code hooks:

```bash
python scripts/install_hooks.py
```

This will:
1. Create/update `~/.claude/settings.json` with hook configuration
2. Point to the `hook_wrapper.sh` script
3. Copy any custom commands to `~/.claude/commands/`

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

## Legacy Hook System (Deprecated)

The `builtin/` directory contains the old internal hook system that was designed for JSON-RPC based hooks. This system is deprecated and will be removed in a future version. All hook functionality is now handled through the Claude Code hooks.

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