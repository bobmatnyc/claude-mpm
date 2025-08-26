# Hook Deployment System

The Claude MPM hook deployment system provides seamless integration between Claude Code and claude-mpm, enabling advanced features like response logging, real-time monitoring, and custom commands.

## Overview

The hook deployment system consists of three main components:

1. **Smart Hook Script**: A dynamic bash script that automatically finds and connects to claude-mpm installations
2. **HookInstaller Class**: Python class that manages hook installation, verification, and removal
3. **Configure Command Integration**: CLI commands for managing hooks

## Features

### Smart Hook Detection

The smart hook script (`~/.claude/hooks/claude-mpm-hook.sh`) automatically detects claude-mpm installations using multiple methods:

1. **Pip-installed packages**: Detects claude-mpm installed via pip
2. **Development environments**: Finds local development installations
3. **Virtual environments**: Properly activates and uses virtual environments
4. **Multiple search paths**: Checks common development locations

This means the hook works regardless of:
- Where claude-mpm is installed
- Whether it's a pip package or local development
- Which Python environment is being used

### Automatic Environment Setup

The hook script automatically:
- Activates virtual environments when found
- Sets up PYTHONPATH for development installs
- Selects the appropriate Python interpreter
- Configures Socket.IO ports for event streaming

## Installation

### Quick Install

The easiest way to install hooks is through the configure command:

```bash
# Install hooks (will not overwrite existing hooks)
claude-mpm configure --install-hooks

# Force reinstall (overwrites existing hooks)
claude-mpm configure --install-hooks --force
```

### Verification

Verify that hooks are properly installed:

```bash
# Check hook installation status
claude-mpm configure --verify-hooks
```

This command checks:
- Hook script exists and is executable
- Claude settings are properly configured
- All required events are registered
- claude-mpm package is accessible

### Uninstallation

Remove hooks when no longer needed:

```bash
# Uninstall hooks
claude-mpm configure --uninstall-hooks
```

## How It Works

### Event Flow

1. Claude Code triggers an event (e.g., Stop, SubagentStop)
2. Claude Code calls the configured hook script
3. The smart hook script:
   - Finds the claude-mpm installation
   - Sets up the Python environment
   - Calls the Python hook handler
4. The Python handler processes the event and returns a response

### Configured Events

The hook system listens for these Claude Code events:

- **UserPromptSubmit**: When a user submits a prompt
- **PreToolUse**: Before a tool is executed
- **PostToolUse**: After a tool completes
- **Stop**: When the main agent stops
- **SubagentStop**: When a subagent completes

### Response Logging

For response logging to work:
1. Hooks must be installed
2. The Stop and SubagentStop events must be configured
3. Response logging must be enabled in claude-mpm configuration

## Troubleshooting

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
# Enable debug mode
export CLAUDE_MPM_HOOK_DEBUG=true

# Check debug log
tail -f /tmp/claude-mpm-hook.log
```

### Common Issues

#### Hooks Not Triggering

1. Verify hooks are installed: `claude-mpm configure --verify-hooks`
2. Check Claude settings: `cat ~/.claude/settings.json`
3. Ensure hook script is executable: `ls -la ~/.claude/hooks/`

#### Python Import Errors

1. Check Python environment: `which python3`
2. Verify claude-mpm is installed: `pip show claude-mpm`
3. Test import manually: `python3 -c "import claude_mpm"`

#### Hook Returns Error

1. Check error log: `cat /tmp/claude-mpm-hook-error.log`
2. Enable debug mode and check detailed logs
3. Verify Socket.IO port is available (default: 8765)

### Manual Testing

Test the hook script directly:

```bash
# Basic test
~/.claude/hooks/claude-mpm-hook.sh test

# With debug output
CLAUDE_MPM_HOOK_DEBUG=true ~/.claude/hooks/claude-mpm-hook.sh test
```

Expected output: `{"action": "continue"}`

## Advanced Configuration

### Custom Search Paths

The smart hook script searches these locations by default:
- `$HOME/Projects/claude-mpm`
- `$HOME/projects/claude-mpm`
- `$HOME/dev/claude-mpm`
- `$HOME/Development/claude-mpm`
- `$HOME/src/claude-mpm`
- `$HOME/code/claude-mpm`
- `$HOME/workspace/claude-mpm`
- Current directory

### Environment Variables

Control hook behavior with environment variables:

- `CLAUDE_MPM_HOOK_DEBUG`: Enable debug logging
- `CLAUDE_MPM_SOCKETIO_PORT`: Socket.IO port (default: 8765)
- `CLAUDE_MPM_LOG_LEVEL`: Logging level for Python handler

## Security Considerations

The hook system is designed with security in mind:

1. **No hardcoded paths**: Dynamically finds installations
2. **Graceful failure**: Returns "continue" on any error to not block Claude
3. **Isolated execution**: Each hook call is independent
4. **No persistent state**: Hooks don't maintain state between calls

## Integration with Other Features

The hook system enables several claude-mpm features:

- **Response Logging**: Captures and logs agent responses
- **Real-time Monitoring**: Streams events to the dashboard
- **Custom Commands**: Enables /mpm commands in Claude Code
- **Performance Tracking**: Monitors tool usage and timing

## For Developers

### Extending the Hook System

To add new hook functionality:

1. Edit the Python handler: `src/claude_mpm/hooks/claude_hooks/hook_handler.py`
2. Add new event processing logic
3. Update the hook configuration if needed
4. Test with the verification command

### Hook Handler API

The Python hook handler must:
- Accept event data as command-line arguments
- Return JSON with an "action" field
- Handle errors gracefully
- Complete quickly (< 1 second ideally)

Example response:
```json
{
  "action": "continue",
  "metadata": {
    "processed": true,
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

## See Also

- [Response Logging Configuration](../03-features/response-logging.md)
- [Real-time Monitoring](../03-features/monitoring.md)
- [CLI Commands Reference](../02-commands/configure.md)