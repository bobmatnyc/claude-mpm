# Commander Auto-Start Feature

## Overview

The `claude-mpm commander` subcommand now automatically starts the Commander daemon and launches the interactive chat interface in a single command.

## Features

### Auto-Start Daemon
- Checks if daemon is already running at `http://{host}:{port}/api/health`
- If not running, starts the daemon in a background thread
- Waits up to 3 seconds for daemon to become ready
- If daemon already running, reuses the existing instance

### Interactive Chat
- After daemon starts (or if already running), launches the Commander REPL
- Provides natural language interface for managing Claude Code instances
- Supports tmux-based session management

### Daemon-Only Mode
- Use `--daemon-only` or `--no-chat` to start daemon without chat interface
- Useful for background services or API-only usage
- Keeps process running until interrupted (Ctrl+C)

## Usage

### Start Commander (daemon + chat)
```bash
claude-mpm commander
```

This will:
1. Check if daemon is running on `127.0.0.1:8765`
2. Start daemon if not running
3. Launch interactive chat REPL

### Start Daemon Only
```bash
claude-mpm commander --daemon-only
```

This will:
1. Check if daemon is running
2. Start daemon if not running
3. Keep process running (no chat interface)
4. Print API URL and wait for Ctrl+C

### Custom Port and Host
```bash
claude-mpm commander --port 9000 --host 0.0.0.0
```

### Debug Mode
```bash
claude-mpm commander --debug
```

## Options

| Option | Description | Default |
|--------|-------------|---------|
| `--port` | Daemon port | 8765 |
| `--host` | Daemon host | 127.0.0.1 |
| `--state-dir` | State persistence directory | ~/.claude-mpm/commander |
| `--no-chat` | Start daemon only (no chat) | false |
| `--daemon-only` | Alias for --no-chat | false |
| `--debug` | Enable debug logging | false |

## Architecture

### Components

1. **CLI Parser** (`commander_parser.py`)
   - Defines command-line arguments
   - Provides help text and examples

2. **Command Handler** (`commands/commander.py`)
   - Auto-starts daemon if needed
   - Launches chat interface
   - Handles daemon-only mode

3. **Daemon** (`commander/daemon.py`)
   - Main daemon process
   - Runs FastAPI server with REST API
   - Manages project sessions

4. **Chat CLI** (`commander/chat/cli.py`)
   - Interactive REPL interface
   - Sends commands to daemon
   - Displays output

### Daemon Health Check

The command checks daemon health via HTTP:

```python
GET http://{host}:{port}/api/health
```

Expected response:
```json
{
  "status": "ok",
  "projects": 0
}
```

### Daemon Startup

The daemon is started in a background thread using:

```python
daemon_thread = threading.Thread(
    target=lambda: asyncio.run(daemon_main(config)),
    daemon=True
)
daemon_thread.start()
```

The daemon thread is marked as daemon so it won't prevent process exit.

## Implementation Details

### File Changes

1. **`cli/parsers/commander_parser.py`**
   - Added `--host` argument
   - Added `--no-chat` flag
   - Added `--daemon-only` alias
   - Updated help text

2. **`cli/commands/commander.py`**
   - Added daemon health check logic
   - Added daemon auto-start in background thread
   - Added daemon-only mode handling
   - Added proper error handling

### Error Handling

- **Daemon start timeout**: Returns exit code 1 if daemon doesn't start within 3 seconds
- **Connection errors**: Treats as daemon not running, attempts to start
- **Keyboard interrupt**: Gracefully exits with code 0
- **Unexpected errors**: Logs error and returns exit code 1

## Examples

### Example 1: First-time startup
```bash
$ claude-mpm commander
Starting Commander daemon on 127.0.0.1:8765...
✓ Commander daemon started

Launching Commander chat interface...

Commander REPL v1.0.0
Type 'help' for available commands, 'exit' to quit.

>
```

### Example 2: Daemon already running
```bash
$ claude-mpm commander
✓ Commander daemon already running on 127.0.0.1:8765

Launching Commander chat interface...

Commander REPL v1.0.0
Type 'help' for available commands, 'exit' to quit.

>
```

### Example 3: Daemon-only mode
```bash
$ claude-mpm commander --daemon-only
Starting Commander daemon on 127.0.0.1:8765...
✓ Commander daemon started

Daemon running. API at http://127.0.0.1:8765
Press Ctrl+C to stop

^C
Shutting down...
```

## Testing

### Test daemon health check
```bash
# Start daemon in one terminal
claude-mpm commander --daemon-only

# In another terminal, verify health endpoint
curl http://127.0.0.1:8765/api/health
```

### Test auto-start with existing daemon
```bash
# Start daemon
claude-mpm commander --daemon-only &

# Launch chat (should detect existing daemon)
claude-mpm commander
```

### Test custom port
```bash
# Start on custom port
claude-mpm commander --port 9000 --daemon-only

# Verify
curl http://127.0.0.1:9000/api/health
```

## Future Enhancements

1. **Graceful daemon shutdown**: Add signal handling to stop daemon thread properly
2. **Daemon status command**: `claude-mpm commander status` to check if running
3. **Daemon restart**: `claude-mpm commander restart` to force restart
4. **Multiple daemons**: Support for multiple daemons on different ports
5. **Daemon logs**: `claude-mpm commander logs` to view daemon output

## Related Documentation

- [Commander Architecture](./commander-architecture.md)
- [Commander API Reference](./commander-api.md)
- [Commander REPL Commands](./commander-repl.md)
