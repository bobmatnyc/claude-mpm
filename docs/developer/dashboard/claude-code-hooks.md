# Claude Code Hook Handling

This document explains how Claude Code hooks are processed and integrated with the WebSocket system for real-time monitoring.

## Overview

Claude Code provides a hook system that allows external programs to intercept and respond to various events during code execution. Claude MPM uses these hooks to broadcast events to the dashboard.

## Hook Types

### 1. UserPromptSubmit

Triggered when the user submits a prompt (presses Enter).

**Event Data**:
```json
{
    "hook_event_name": "UserPromptSubmit",
    "prompt": "User's input text",
    "session_id": "unique-session-id",
    "cwd": "/current/working/directory",
    "claude_pid": 12345,
    "timestamp": "2025-07-31T12:00:00Z"
}
```

**Use Cases**:
- Monitor user interactions
- Intercept `/mpm` commands
- Track prompt history

### 2. PreToolUse

Triggered before Claude uses a tool (Read, Edit, Bash, etc.).

**Event Data**:
```json
{
    "hook_event_name": "PreToolUse",
    "tool_name": "Edit",
    "tool_input": {
        "file_path": "/path/to/file.py",
        "old_string": "...",
        "new_string": "..."
    },
    "session_id": "unique-session-id",
    "cwd": "/current/working/directory"
}
```

**Use Cases**:
- Monitor tool usage
- Block dangerous operations
- Log file modifications

### 3. PostToolUse

Triggered after a tool completes execution.

**Event Data**:
```json
{
    "hook_event_name": "PostToolUse",
    "tool_name": "Bash",
    "tool_input": {"command": "ls -la"},
    "tool_output": "file listing...",
    "exit_code": 0,
    "session_id": "unique-session-id"
}
```

**Use Cases**:
- Track execution results
- Monitor command outputs
- Detect errors

## Hook Handler Implementation

### Optimized Hook Handler

**Location**: `src/claude_mpm/hooks/claude_hooks/hook_handler.py`

The hook handler is optimized for minimal latency:

```python
class ClaudeHookHandler:
    def __init__(self):
        # Get WebSocket server/proxy
        self.websocket_server = get_websocket_server()
        if hasattr(self.websocket_server, 'start'):
            self.websocket_server.start()
    
    def handle(self):
        # Read event from stdin
        event_data = sys.stdin.read()
        event = json.loads(event_data)
        
        # Fast path for common events
        hook_type = event.get('hook_event_name')
        if hook_type == 'UserPromptSubmit':
            self._handle_user_prompt_fast(event)
        # ... handle other events
        
        # Always continue
        print(json.dumps({"action": "continue"}))
```

### Key Optimizations

1. **No File I/O**: Removed all debug file writes
2. **Async Broadcasting**: Events sent without blocking
3. **Minimal Processing**: Only essential data extracted
4. **Fast Failure**: Errors ignored to prevent blocking

## Hook Configuration

### Settings File

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }],
    "PreToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }],
    "PostToolUse": [{
      "matcher": "*",
      "hooks": [{
        "type": "command",
        "command": "/path/to/hook_wrapper.sh"
      }]
    }]
  }
}
```

### Hook Wrapper Script

The wrapper script handles environment setup:

```bash
#!/bin/bash
# hook_wrapper.sh

# Detect environment (dev vs installed)
if [ -d "$SCRIPT_DIR/../../../../venv" ]; then
    # Development environment
    PROJECT_ROOT="$( cd "$SCRIPT_DIR/../../../.." && pwd )"
    export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
fi

# Run the Python hook handler
exec "$PYTHON_CMD" "$SCRIPT_DIR/hook_handler.py" "$@"
```

## Event Broadcasting

### Event Processing Flow

1. **Event Reception**:
   ```python
   event_data = sys.stdin.read()
   event = json.loads(event_data)
   ```

2. **Data Extraction**:
   ```python
   prompt = event.get('prompt', '')
   session_id = event.get('session_id', '')
   ```

3. **Broadcasting**:
   ```python
   self.websocket_server.broadcast_event('hook.user_prompt', {
       'prompt': prompt[:200],  # Truncate
       'session_id': session_id,
       'timestamp': datetime.now().isoformat()
   })
   ```

### Broadcast Event Types

- `hook.user_prompt` - User prompt submission
- `hook.pre_tool_use` - Before tool execution
- `hook.post_tool_use` - After tool execution
- `agent.delegation` - Agent task delegation
- `todo.update` - Todo list changes

## Performance Considerations

### Latency Sources

1. **File I/O** - Eliminated
2. **Synchronous WebSocket** - Made async
3. **Large Payloads** - Truncated
4. **Error Handling** - Fail silently

### Benchmarks

- Hook processing: < 1ms
- WebSocket send: < 5ms (async)
- Total overhead: < 10ms

## Special Handling

### MPM Commands

The hook handler intercepts `/mpm` commands:

```python
if prompt.startswith('/mpm'):
    # Special handling for MPM commands
    return  # Don't broadcast
```

### Tool Output Truncation

Large outputs are truncated to prevent performance issues:

```python
def _get_tool_output_preview(self, tool_name: str, output: str) -> str:
    if tool_name in ['Bash', 'Read']:
        return output[:500] + '...' if len(output) > 500 else output
    return output[:200] + '...' if len(output) > 200 else output
```

### Session Filtering

Events include session_id for filtering:

```python
'session_id': event.get('session_id', '')
```

## Debugging

### Enable Debug Mode

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

### Check Hook Execution

```bash
# Test hook handler directly
echo '{"hook_event_name": "test"}' | python hook_handler.py
```

### Monitor Events

```bash
# Watch WebSocket events
python scripts/monitor_websocket_events.py
```

## Common Issues

### Hooks Not Firing

1. Check `.claude/settings.json` exists
2. Verify hook script is executable
3. Ensure correct path in settings

### Events Not Broadcasting

1. Check WebSocket server is running
2. Verify hook handler can import websocket_server
3. Check for Python import errors

### Latency Issues

1. Ensure optimized handler is used
2. Check for blocking operations
3. Verify async broadcasting

## Best Practices

1. **Keep handlers fast** - < 10ms total
2. **Fail silently** - Don't block Claude
3. **Truncate data** - Limit payload size
4. **Use session IDs** - Enable filtering
5. **Avoid file I/O** - Use WebSocket only