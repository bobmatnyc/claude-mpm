# Commander Chat Interface Guide

## Overview

The Commander provides an interactive chat interface for managing multiple Claude Code instances. This interface allows you to start, stop, and communicate with multiple Claude instances simultaneously, switching between them seamlessly.

## Quick Start

Launch the Commander chat interface:

```bash
claude-mpm commander
```

You'll see the Commander prompt:

```
Commander>
```

## Core Concepts

### Instances

An **instance** is a running Claude Code or MPM session in a dedicated tmux pane. Each instance:
- Runs in its own project directory
- Has a unique name for identification
- Uses a specific framework (Claude Code or MPM)
- Maintains its own session state and history

### Frameworks

Commander supports two frameworks:
- **`cc`** - Claude Code (official CLI)
- **`mpm`** - Claude MPM (multi-agent orchestration)

### Session Context

The session context tracks:
- Current connection status
- Connected instance name
- Message history for the session
- Session metadata

## Commands Reference

### Instance Management

#### `list` / `ls`
List all active instances.

```
Commander> list
Active instances:
  → myapp (cc) - ~/Projects/myapp [main]
  → backend (mpm) - ~/Projects/backend [feature/auth]
```

Shows:
- Instance name
- Framework type
- Project path
- Git branch (if available)

#### `start <path> [options]`
Start a new instance.

**Options:**
- `--framework <cc|mpm>` - Framework to use (default: `cc`)
- `--name <name>` - Custom instance name (default: directory name)

**Examples:**

```bash
# Start Claude Code in current directory
Commander> start .

# Start with specific framework and name
Commander> start ~/Projects/myapp --framework cc --name myapp

# Start MPM instance
Commander> start ~/Projects/backend --framework mpm --name backend
```

#### `stop <name>`
Stop a running instance.

```
Commander> stop myapp
✓ Instance 'myapp' stopped
```

### Connection Management

#### `connect <name>`
Connect to an instance to send messages.

```
Commander> connect myapp
Connected to myapp
Commander (myapp)>
```

Once connected:
- The prompt shows the connected instance name
- Regular messages are sent directly to the instance
- Commands still work with the `!` prefix

#### `disconnect`
Disconnect from the current instance.

```
Commander (myapp)> disconnect
Disconnected from myapp
Commander>
```

#### `status`
Show current connection status and instance information.

```
Commander (myapp)> status
Connected to: myapp
Framework: cc
Project: ~/Projects/myapp
Branch: main
Status: clean
```

### Chat Interaction

When connected to an instance, simply type your message:

```
Commander (myapp)> show me the project structure

[Response from myapp]:
The project structure is:
- src/
  - main.py
  - utils.py
- tests/
  - test_main.py
- README.md
```

**Tips:**
- Messages are sent directly to the connected instance
- Use natural language as you would with Claude
- The instance maintains context across messages
- Long outputs are automatically summarized (if configured)

### Help and Exit

#### `help`
Show available commands.

```
Commander> help
Commander Commands:
  list, ls              - List active instances
  start <path>          - Start new instance
  stop <name>           - Stop an instance
  connect <name>        - Connect to instance
  disconnect            - Disconnect from current
  status                - Show connection status
  help                  - Show this help
  exit, quit            - Exit Commander
```

#### `exit` / `quit`
Exit the Commander interface.

```
Commander> exit
Goodbye!
```

**Note:** Exiting Commander does NOT stop running instances. They continue running in the background. Use `stop` to terminate instances.

## Workflow Examples

### Basic Workflow

1. **Start an instance**
   ```
   Commander> start ~/Projects/myapp --framework cc --name myapp
   ✓ Instance 'myapp' started (tmux: mpm-commander-myapp)
   ```

2. **Connect to it**
   ```
   Commander> connect myapp
   Connected to myapp
   Commander (myapp)>
   ```

3. **Chat with the instance**
   ```
   Commander (myapp)> analyze the codebase and suggest improvements

   [Response from myapp]:
   I've analyzed your codebase. Here are my suggestions:
   1. Add type hints to main.py
   2. Refactor utils.py for better modularity
   3. Add integration tests
   ```

4. **Disconnect when done**
   ```
   Commander (myapp)> disconnect
   Disconnected from myapp
   ```

5. **Stop the instance (optional)**
   ```
   Commander> stop myapp
   ✓ Instance 'myapp' stopped
   ```

### Multi-Instance Workflow

Manage multiple projects simultaneously:

```bash
# Start instances for different projects
Commander> start ~/Projects/frontend --name frontend --framework cc
Commander> start ~/Projects/backend --name backend --framework mpm
Commander> start ~/Projects/mobile --name mobile --framework cc

# List all running instances
Commander> list
Active instances:
  → frontend (cc) - ~/Projects/frontend
  → backend (mpm) - ~/Projects/backend
  → mobile (cc) - ~/Projects/mobile

# Work on frontend
Commander> connect frontend
Commander (frontend)> add a login form to the dashboard

# Switch to backend
Commander (frontend)> connect backend
Commander (backend)> implement the authentication API

# Switch to mobile
Commander (backend)> connect mobile
Commander (mobile)> integrate the login API

# Stop instances when done
Commander> disconnect
Commander> stop frontend
Commander> stop backend
Commander> stop mobile
```

### Debugging Workflow

Use Commander to coordinate debugging across components:

```bash
# Start instances for service and tests
Commander> start ~/Projects/myservice --name service
Commander> start ~/Projects/myservice --name tests

# Connect to service instance
Commander> connect service
Commander (service)> add debug logging to the request handler

# Switch to tests
Commander (service)> connect tests
Commander (tests)> run the integration tests with verbose output

# Review and iterate
Commander (tests)> disconnect
Commander> status
```

## Advanced Features

### Output Summarization

When instances produce verbose output (like test results or file listings), the Commander can automatically summarize it for easier reading.

**Configuration:**
Set the `OPENROUTER_API_KEY` environment variable to enable summarization:

```bash
export OPENROUTER_API_KEY="sk-..."  # pragma: allowlist secret
```

**How it works:**
- Long outputs (>1000 characters) are detected
- Key information is extracted and summarized
- Summary is displayed instead of full output
- Full output is still available in the instance's tmux pane

### Session Persistence

Commander maintains session state including:
- Active instances across restarts
- Message history for each session
- Connection state
- Instance metadata

**State Location:**
```
~/.claude-mpm/commander/
  sessions/
    <session-id>.json
```

### Git Integration

Commander automatically detects and displays git information:
- Current branch name
- Working directory status (clean/modified)
- Uncommitted changes count

This appears in:
- `list` command output
- `status` command output
- Instance metadata

## Configuration

### Environment Variables

- **`OPENROUTER_API_KEY`** - Required for output summarization
- **`COMMANDER_TMUX_SESSION`** - Custom tmux session name (default: `mpm-commander`)
- **`COMMANDER_STATE_DIR`** - Custom state directory (default: `~/.claude-mpm/commander`)

### State Directory

Session state is saved to:
```
~/.claude-mpm/commander/
  sessions/           # Session state files
  instances/          # Instance metadata
  logs/              # Command logs
```

## Troubleshooting

### Instance Not Starting

**Problem:** `start` command fails or times out

**Solutions:**
1. Verify tmux is installed: `which tmux`
2. Check project path exists: `ls <path>`
3. Ensure framework is installed
4. Check logs: `~/.claude-mpm/commander/logs/`

### Cannot Connect to Instance

**Problem:** `connect` command says instance not found

**Solutions:**
1. List instances: `list`
2. Verify instance is running: `tmux ls`
3. Check instance name spelling
4. Restart instance if needed

### Messages Not Being Sent

**Problem:** Messages appear to send but instance doesn't respond

**Solutions:**
1. Check connection status: `status`
2. Verify instance is responsive in tmux directly
3. Check instance logs for errors
4. Reconnect: `disconnect` then `connect <name>`

### Output Not Summarized

**Problem:** Long outputs aren't being summarized

**Solutions:**
1. Verify `OPENROUTER_API_KEY` is set
2. Check API key is valid
3. Review summarization logs
4. Ensure output length threshold is met (>1000 chars)

## Best Practices

### Instance Naming

- Use descriptive names: `frontend`, `backend`, `api-tests`
- Avoid spaces: use hyphens or underscores
- Keep names short for easier typing
- Use consistent naming across projects

### Session Management

- Disconnect when not actively chatting
- Stop instances when completely done
- List instances periodically to avoid orphans
- Clean up stopped instances

### Message Organization

- One task per message for clarity
- Be specific about file paths and requirements
- Reference previous messages when needed
- Use follow-up questions to refine responses

### Multi-Instance Coordination

- Start all needed instances at beginning
- Name instances by role (e.g., `service`, `tests`, `docs`)
- Keep track of which instance does what
- Stop instances in reverse order of dependencies

## Tips and Tricks

### Quick Commands

Use command aliases:
- `ls` instead of `list`
- `q` or `exit` to quit
- Tab completion for instance names (if available)

### Workflow Templates

Save common workflows as shell aliases:

```bash
# ~/.bashrc or ~/.zshrc
alias cmd-dev='claude-mpm commander'
alias cmd-test='claude-mpm commander --framework mpm'
```

### Integration with tmux

Access instances directly via tmux when needed:

```bash
# List Commander instances
tmux list-panes -t mpm-commander

# Attach to Commander session
tmux attach -t mpm-commander

# Send command to specific pane
tmux send-keys -t mpm-commander:%1 "your command" Enter
```

### Batch Operations

Start multiple instances with a script:

```bash
#!/bin/bash
# start-dev-env.sh

claude-mpm commander << EOF
start ~/Projects/frontend --name frontend
start ~/Projects/backend --name backend
start ~/Projects/mobile --name mobile
list
EOF
```

## Next Steps

- **[Commander API Reference](./commander-api.md)** - REST API documentation
- **[Usage Guide](./usage-guide.md)** - Complete Commander guide
- **[Phase 2 Scope](./phase2-scope.md)** - Implementation details
- **[Output Parser](./output-parser.md)** - Output processing system

## Support

For issues or questions:
- GitHub Issues: [claude-mpm/issues](https://github.com/your-org/claude-mpm/issues)
- Documentation: [docs/commander/](.)
- Examples: [examples/](../../examples/)
