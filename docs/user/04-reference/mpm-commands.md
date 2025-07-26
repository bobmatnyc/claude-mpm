# MPM Commands Reference

This guide documents the MPM command system in Claude MPM, including the `/mpm:` command prefix, available commands, and how to use them effectively.

## Overview

Claude MPM provides a special command system that allows you to execute local commands without sending them to Claude. These commands are prefixed with `/mpm:` and are intercepted and processed locally by the MPM framework.

## Command Syntax

MPM commands follow this syntax:
```
/mpm:<command> [arguments]
```

Examples:
- `/mpm:test` - Run the test command
- `/mpm:status` - Check system status (future command)
- `/mpm:help` - Show available commands (future command)

## Available Commands

### Currently Implemented

#### `/mpm:test`
A simple test command that returns "Hello World". This command is primarily used for testing the command interception system.

**Usage:**
```bash
/mpm:test
```

**Output:**
```
Hello World
```

### Planned Commands (Not Yet Implemented)

The MPM command system is designed to be extensible. Future commands may include:

- `/mpm:status` - Show MPM system status
- `/mpm:agents` - List available agents
- `/mpm:config` - Manage configuration
- `/mpm:help` - Show command help

## Usage Modes

### Non-Interactive Mode

In non-interactive mode, MPM commands work automatically:

```bash
# Direct command execution
./claude-mpm run -i "/mpm:test" --non-interactive

# From a file
echo "/mpm:test" > command.txt
./claude-mpm run -i command.txt --non-interactive

# Using the shortened form
./claude-mpm run -i "/mpm:test" -n
```

### Interactive Mode

For interactive mode, you need to enable command interception:

```bash
# Start with command interception enabled
./claude-mpm run --intercept-commands

# Or use the shorter form
./claude-mpm --intercept-commands
```

When command interception is enabled:
- Type `/mpm:test` at any prompt to execute the command
- The command is handled locally without sending to Claude
- Normal prompts continue to be sent to Claude as usual

## How MPM Commands Work

### Command Flow

1. **Input Detection**: When you enter a prompt, the system checks if it starts with `/mpm:`
2. **Local Handling**: If it's an MPM command, it's processed locally by the `_handle_mpm_command` method
3. **Direct Response**: The command output is returned directly without involving Claude
4. **Normal Processing**: Non-MPM prompts are sent to Claude as usual

### Architecture

The MPM command system consists of several components:

#### 1. Simple Runner Handler
Located in `src/claude_mpm/core/simple_runner.py`, this handles basic command interception:

```python
def _handle_mpm_command(self, prompt: str) -> bool:
    """Handle /mpm: commands directly without going to Claude."""
    # Extracts command after /mpm:
    # Executes command
    # Returns response directly
```

#### 2. Interactive Wrapper
When using `--intercept-commands`, the interactive wrapper (`scripts/interactive_wrapper.py`):
- Maintains a conversation loop
- Checks each input for `/mpm:` prefix
- Routes commands appropriately

#### 3. Hook System Integration
The `MpmCommandHook` in `src/claude_mpm/hooks/builtin/mpm_command_hook.py` provides hook-based command handling:
- Priority: 1 (highest)
- Can route to external command handlers
- Supports more complex command processing

#### 4. Command Router
The command router (`/.claude/scripts/command_router.py`) provides a extensible command dispatch system:
- Registers command handlers
- Executes commands with arguments
- Returns results to the caller

## Agent Command Shortcuts

While not implemented as MPM commands, Claude MPM supports agent-specific task delegation through the Task tool. You can delegate to agents using either format:

**Capitalized format:**
```
Task(description="Research the authentication patterns", subagent_type="Research")
Task(description="Implement the login endpoint", subagent_type="Engineer")
Task(description="Write tests for the API", subagent_type="QA")
```

**Lowercase format:**
```
Task(description="Research the authentication patterns", subagent_type="research")
Task(description="Implement the login endpoint", subagent_type="engineer")
Task(description="Write tests for the API", subagent_type="qa")
```

Available agents:
- `engineer` / `Engineer` - For coding and implementation
- `qa` / `QA` - For testing and quality assurance
- `documentation` / `Documentation` - For documentation tasks
- `research` / `Research` - For investigation and analysis
- `security` / `Security` - For security-related tasks
- `ops` / `Ops` - For deployment and infrastructure
- `version-control` / `Version Control` - For git operations
- `data-engineer` / `Data Engineer` - For data processing

## Common Workflows

### Testing Command Interception

1. **Quick Test**:
   ```bash
   ./claude-mpm run -i "/mpm:test" --non-interactive
   ```

2. **Interactive Testing**:
   ```bash
   ./claude-mpm --intercept-commands
   # Then type: /mpm:test
   ```

### Using Aliases

Users often create shell aliases for common operations:

```bash
# Quick access to MPM
alias cm='claude-mpm'
alias cmr='claude-mpm run'

# Test MPM commands
alias mpm-test='claude-mpm run -i "/mpm:test" --non-interactive'

# Interactive with command interception
alias cmi='claude-mpm --intercept-commands'
```

### Batch Processing

You can create files with multiple MPM commands:

```bash
# Create a command file
cat > commands.txt << EOF
/mpm:test
Regular prompt for Claude
/mpm:test
Another prompt for Claude
EOF

# Run in non-interactive mode
./claude-mpm run -i commands.txt --non-interactive
```

## Extending MPM Commands

### Adding New Commands

To add a new MPM command:

1. **Update the Simple Runner** (`src/claude_mpm/core/simple_runner.py`):
   ```python
   def _handle_mpm_command(self, prompt: str) -> bool:
       # ... existing code ...
       
       if command == "test":
           print("Hello World")
           return True
       elif command == "status":  # New command
           print("System status: OK")
           return True
   ```

2. **Update the Command Router** (if using hook system):
   ```python
   def _register_builtin_commands(self):
       self.register("test", self._test_command)
       self.register("status", self._status_command)  # New
   
   def _status_command(self, *args) -> str:
       return "System status: OK"
   ```

3. **Update Help Messages** in both:
   - Command handler help text
   - Interactive wrapper welcome message

### Best Practices

1. **Command Naming**: Use lowercase, hyphen-separated names (e.g., `get-status`)
2. **Error Handling**: Always provide clear error messages
3. **Documentation**: Update this reference when adding new commands
4. **Testing**: Test in both interactive and non-interactive modes

## Troubleshooting

### Command Not Recognized

If your MPM command isn't recognized:
1. Ensure you're using the correct prefix: `/mpm:`
2. Check if command interception is enabled in interactive mode
3. Verify the command is implemented in the handler

### Interactive Mode Issues

If commands aren't being intercepted in interactive mode:
1. Make sure you started with `--intercept-commands`
2. Check that the interactive wrapper is running
3. Try using non-interactive mode to isolate the issue

### Testing Commands

Use the test script to verify command functionality:
```bash
python scripts/test_mpm_command.py
```

This tests:
- Non-interactive mode execution
- Interactive wrapper functionality
- CLI with --intercept-commands flag

## Future Enhancements

The MPM command system is designed to grow. Planned enhancements include:

1. **Plugin System**: Allow external command plugins
2. **Command Discovery**: Auto-discover commands from `.claude/commands/`
3. **Rich Output**: Support for formatted output and tables
4. **Command History**: Track and replay previous commands
5. **Agent Commands**: Direct shortcuts like `/engineer:`, `/qa:`, etc.

## Related Documentation

- [MPM Command Interception Design](../../design/MPM_COMMAND_INTERCEPTION.md)
- [Hook System](../../developer/02-core-components/hook-system.md)
- [CLI Reference](./cli-reference.md)
- [Agent System](../../developer/02-core-components/agent-system.md)