# AutoTodos: Automatic Todo Generation from Hook Errors

## Overview

AutoTodos is a POC feature that automatically converts hook errors into actionable todos for the PM. This enables automated error handling and delegation without manual todo creation.

## Concept

When hook errors are detected (stored in `.claude-mpm/hook_errors.json`), AutoTodos can:
1. **List** them as pending todos
2. **Inject** them into the PM's todo list
3. **Clear** them after resolution

## Commands

### `claude-mpm autotodos status`
Show summary of hook errors and pending todos.

```bash
claude-mpm autotodos status
```

**Output:**
```
📊 AutoTodos Status
================================================================================
Total Errors: 0
Pending Todos: 0 (errors with 2+ occurrences)
Unique Errors: 0

📁 Memory File: /Users/masa/Projects/claude-mpm/.claude-mpm/hook_errors.json

✅ No pending todos. All hook errors are resolved!
```

### `claude-mpm autotodos list`
List all auto-generated todos from hook errors.

```bash
# Table format (default)
claude-mpm autotodos list

# JSON format
claude-mpm autotodos list --format json
```

**Example Output (when errors exist):**
```
================================================================================
Auto-Generated Todos from Hook Errors
================================================================================

1. Fix PreToolUse hook error: command_not_found (git) [3 occurrences]
   Status: pending
   Hook: PreToolUse
   Error Type: command_not_found
   First Seen: 2026-01-07T22:00:00Z
   Last Seen: 2026-01-07T22:15:00Z

================================================================================
Total: 1 pending todo(s)

To inject into PM session: claude-mpm autotodos inject
```

### `claude-mpm autotodos inject`
Inject auto-generated todos in PM-compatible format.

```bash
# Output to stdout (for piping)
claude-mpm autotodos inject

# Output to file
claude-mpm autotodos inject --output todos.json
```

**Output Format:**
```json
{
  "type": "autotodos",
  "timestamp": "2026-01-07T22:30:00Z",
  "todos": [
    {
      "content": "Fix PreToolUse hook error: command_not_found (git) [3 occurrences]",
      "activeForm": "Fixing PreToolUse hook error",
      "status": "pending",
      "metadata": {
        "error_key": "command_not_found:PreToolUse:git",
        "error_type": "command_not_found",
        "hook_type": "PreToolUse",
        "details": "git",
        "count": 3,
        "first_seen": "2026-01-07T22:00:00Z",
        "last_seen": "2026-01-07T22:15:00Z"
      }
    }
  ],
  "message": "Found 1 hook error(s) requiring attention. Consider delegating to appropriate agents for resolution."
}
```

### `claude-mpm autotodos clear`
Clear hook errors after resolution.

```bash
# Clear all errors
claude-mpm autotodos clear

# Clear specific error
claude-mpm autotodos clear --error-key "command_not_found:PreToolUse:git"

# Skip confirmation
claude-mpm autotodos clear -y
```

## Todo Format

Each auto-generated todo includes:

- **content**: Description of the hook error (imperative form)
- **activeForm**: Present continuous form for in-progress display
- **status**: Always "pending" (PM will update when working on it)
- **metadata**: Full error details including:
  - `error_key`: Unique identifier
  - `error_type`: Type of error (command_not_found, file_not_found, etc.)
  - `hook_type`: Which hook failed (PreToolUse, PostToolUse, etc.)
  - `details`: Specific error details
  - `count`: Number of occurrences
  - `first_seen` / `last_seen`: Timestamps

## Integration with PM

### Manual Integration (Current)
1. Run `claude-mpm autotodos inject --output todos.json`
2. Load `todos.json` content
3. Add todos to PM's TodoWrite manually

### Future: Automatic Integration (Planned)
Hook into SessionStart event to automatically inject pending todos:

```python
# Future implementation in event_handlers.py
def handle_session_start_fast(self, event):
    # Check for pending autotodos
    from claude_mpm.cli.commands.autotodos import get_autotodos

    todos = get_autotodos()
    if todos:
        # Inject as system reminder
        system_message = {
            "type": "system_reminder",
            "source": "autotodos",
            "todos": todos,
            "message": f"Found {len(todos)} hook error(s) requiring attention."
        }
        # Send to PM via hook mechanism
        self._emit_autotodos_reminder(system_message)
```

## Error Filtering

Only errors with **2+ occurrences** are included in autotodos:
- **1 occurrence**: Might be transient, not actionable yet
- **2+ occurrences**: Persistent issue requiring attention

This threshold is defined in `get_autotodos()`:
```python
if error_data["count"] >= 2:
    todo = format_error_as_todo(error_key, error_data)
    todos.append(todo)
```

## Workflow

```
Hook Error Detected
        ↓
HookErrorMemory stores error
        ↓
Error count >= 2?
        ↓ Yes
AutoTodos creates todo
        ↓
PM receives todo (inject command or SessionStart hook)
        ↓
PM delegates to appropriate agent
        ↓
Agent resolves issue
        ↓
AutoTodos clear (manual or automatic)
```

## Benefits

1. **Automated Error Tracking**: No manual todo creation for hook errors
2. **PM Delegation**: PM can easily delegate errors to agents
3. **Error Visibility**: Hook errors don't get lost in logs
4. **Actionable Format**: Todos include context and fix suggestions
5. **Persistence Filtering**: Only persistent errors (2+ occurrences) become todos

## Limitations (POC)

1. **Manual Injection**: Requires running `inject` command manually
2. **No Auto-Clearing**: Must manually clear after resolution
3. **No PM Integration**: Not yet hooked into SessionStart event
4. **Simple Format**: Basic todo structure (can be enhanced)

## Future Enhancements

1. **SessionStart Hook**: Auto-inject on PM session start
2. **Auto-Clearing**: Clear todos when underlying error is resolved
3. **Priority Mapping**: Map error severity to todo priority
4. **Fix Suggestions**: Include HookErrorMemory fix suggestions in metadata
5. **Delegation Hints**: Suggest which agent to delegate to based on error type
6. **Error Grouping**: Group related errors into single todo

## Related Files

- **Implementation**: `src/claude_mpm/cli/commands/autotodos.py`
- **CLI Registration**: `src/claude_mpm/cli/executor.py`
- **Parser**: `src/claude_mpm/cli/parsers/base_parser.py`
- **Hook Error Storage**: `src/claude_mpm/core/hook_error_memory.py`
- **Error Data**: `.claude-mpm/hook_errors.json`

## Testing

```bash
# Check status
claude-mpm autotodos status

# List pending todos
claude-mpm autotodos list

# Inject to file
claude-mpm autotodos inject --output /tmp/todos.json

# View injected todos
cat /tmp/todos.json | jq .

# Clear all errors
claude-mpm autotodos clear -y
```
