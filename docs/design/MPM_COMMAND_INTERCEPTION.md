# MPM Command Interception

This document describes the `/mpm:` command interception feature in Claude MPM.

## Overview

Claude MPM can intercept special `/mpm:` commands before they are sent to Claude. This allows for local command execution and enhanced functionality.

## Available Commands

- `/mpm:test` - Returns "Hello World" (used for testing the interception system)

## Usage

### Non-Interactive Mode

The `/mpm:` commands work automatically in non-interactive mode:

```bash
# Direct command
./claude-mpm run -i "/mpm:test" --non-interactive

# From file
echo "/mpm:test" > command.txt
./claude-mpm run -i command.txt --non-interactive
```

### Interactive Mode

For interactive mode, you need to enable command interception:

```bash
# Enable command interception
./claude-mpm run --intercept-commands

# Or use the shorter form
./claude-mpm --intercept-commands
```

When command interception is enabled:
- You can type `/mpm:test` at any prompt
- The command will be handled locally without sending to Claude
- Normal prompts will still be sent to Claude as usual

## Implementation Details

### Command Handler

The command handler is implemented in `src/claude_mpm/core/simple_runner.py`:

```python
def _handle_mpm_command(self, prompt: str) -> bool:
    """Handle /mpm: commands directly without going to Claude."""
    # Extracts command after /mpm:
    # Executes command
    # Returns response directly
```

### Interactive Wrapper

When `--intercept-commands` is used, an interactive wrapper (`scripts/interactive_wrapper.py`) is launched that:
1. Maintains a conversation loop
2. Checks each input for `/mpm:` prefix
3. Handles commands locally or sends to Claude

### Hook System (Future)

The `MpmCommandHook` in `src/claude_mpm/hooks/builtin/mpm_command_hook.py` is designed for future integration with the hook system but is not currently active.

## Adding New Commands

To add a new `/mpm:` command:

1. Update the `_handle_mpm_command` method in `simple_runner.py`
2. Add the command logic
3. Update the help text in both locations:
   - Command handler help message
   - Interactive wrapper welcome message

Example:
```python
if command == "test":
    print("Hello World")
    return True
elif command == "status":
    print("System status: OK")
    return True
```

## Testing

Test the command interception with:

```bash
python scripts/test_mpm_command.py
```

This runs tests for:
- Non-interactive mode
- Interactive wrapper
- CLI with --intercept-commands flag