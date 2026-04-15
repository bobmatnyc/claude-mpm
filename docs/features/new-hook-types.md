# New Hook Types in v6.3.2

## Overview

Claude MPM v6.3.2 introduces three new hook types that provide finer-grained control over Claude Code session lifecycle events. These hooks complement the existing hook system and enable enhanced error handling, state management, and session cleanup.

## New Hook Types

### 1. StopFailure Hook

**Purpose**: Fires when Claude Code stops due to API errors or rate limits

**Event**: Triggered when Claude Code encounters:
- API connection failures
- Rate limit errors (429 status)
- Authentication failures (401, 403 status)
- Timeout errors
- Server errors (5xx status)

**Use Case**: Handle failures gracefully, log error context, notify users, or attempt recovery

### 2. PostCompact Hook

**Purpose**: Fires immediately after `/compact` command executes

**Event**: Triggered after Claude Code compacts the session for memory optimization

**What It Does**: Re-injects Claude MPM state from kuzu-memory into the compacted session
- Restores agent context
- Re-establishes skill availability
- Restores session metadata

**Use Case**: Ensure MPM state is properly restored after session compaction, maintain continuity of agent capabilities

### 3. SessionEnd Hook

**Purpose**: Fires when a session is closed or terminated

**Event**: Triggered on:
- User closes Claude Code
- Session timeout
- Explicit session end command
- Process termination

**What It Does**: Triggers kuzu-memory consolidation
- Archives session memories
- Consolidates learnings
- Persists context for future sessions

**Use Case**: Ensure session data is properly persisted and memories are consolidated before session ends

## Registration in Settings

All hook types are registered in `.claude/settings.json` in v6.3.2:

```json
{
  "hooks": {
    "StopFailure": {
      "enabled": true,
      "handler": "claude-hook-fast.sh"
    },
    "PostCompact": {
      "enabled": true,
      "handler": "claude-hook-fast.sh"
    },
    "SessionEnd": {
      "enabled": true,
      "handler": "claude-hook-fast.sh"
    }
  }
}
```

## Hook Type Enumeration

The `HookType` enum in `src/claude_mpm/hooks/base_hook.py` now includes:

```python
class HookType(str, Enum):
    """Available hook event types"""
    
    # Existing hooks
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    STOP = "Stop"
    SUBAGENT_STOP = "SubagentStop"
    SESSION_START = "SessionStart"
    USER_PROMPT_SUBMIT = "UserPromptSubmit"
    
    # New in v6.3.2
    STOP_FAILURE = "StopFailure"
    POST_COMPACT = "PostCompact"
    SESSION_END = "SessionEnd"
    PERMISSION_REQUEST = "PermissionRequest"
```

## PermissionRequest Hook

Also registered in v6.3.2 migration:

**Purpose**: Fires when Claude Code requests user permissions

**Event**: Triggered when:
- Tool use requires approval
- File access needs user consent
- Command execution needs authorization

**Use Case**: Handle permission flows, log access requests, enforce policies

```json
{
  "hooks": {
    "PermissionRequest": {
      "enabled": true,
      "handler": "claude-hook-fast.sh"
    }
  }
}
```

## Hook Dispatcher

All hooks are dispatched through the centralized hook system:

**Script**: `src/claude_mpm/scripts/claude-hook-fast.sh`

**Handler**: `src/claude_mpm/hooks/model_tier_hook.py`

### Hook Lifecycle

1. **Event triggers** (e.g., API error on StopFailure)
2. **Hook dispatcher called** with hook type and context
3. **Handlers execute** in sequence
4. **Context passed** includes:
   - Hook type
   - Session ID
   - Timestamp
   - Error details (if applicable)

## Configuration Hierarchy

Hooks are configured in order of precedence:

1. **Managed settings** (MDM) — org-enforced
2. **Project settings** — `.claude/settings.local.json`
3. **Team settings** — `.claude/settings.json`
4. **Global settings** — `~/.claude/settings.json`

Local settings override team settings:

```json
{
  ".claude/settings.local.json": {
    "hooks": {
      "StopFailure": {
        "enabled": true,
        "custom_handler": "my-error-handler.sh"
      }
    }
  }
}
```

## Migration: v6.3.2-hook-registration

The v6.3.2 startup migration:

1. **Adds new hooks** to `.claude/settings.json`:
   - `StopFailure`
   - `PostCompact`
   - `SessionEnd`
   - `PermissionRequest`

2. **Preserves existing hooks** (no changes to PreToolUse, PostToolUse, etc.)

3. **Idempotent** - Skips if hooks already registered

4. **Non-blocking** - Failures do not prevent startup

## Usage Examples

### Handling API Failures

Configure a custom StopFailure handler:

```bash
#!/bin/bash
# Handle StopFailure hook - log error and notify

HOOK_TYPE="$1"
SESSION_ID="$2"
ERROR_MESSAGE="$3"

echo "[$(date)] API Error in session $SESSION_ID: $ERROR_MESSAGE" >> ~/claude-mpm-errors.log

# Optional: Send notification
# notify-send "Claude MPM Session Error" "$ERROR_MESSAGE"
```

### Re-injecting State After Compact

PostCompact hook automatically restores MPM context:

```python
# In hook handler
def handle_post_compact(session_id: str) -> None:
    """Re-inject MPM state after session compact"""
    # Load saved MPM context from kuzu-memory
    context = kuzu_memory.load_session_context(session_id)
    
    # Reinject into Claude Code environment
    inject_session_context(context)
```

### Consolidating Session Memories

SessionEnd hook triggers memory consolidation:

```python
# In hook handler
def handle_session_end(session_id: str) -> None:
    """Consolidate memories before session ends"""
    # Get all session memories
    memories = kuzu_memory.get_session_memories(session_id)
    
    # Consolidate and archive
    kuzu_memory.consolidate_memories(session_id, memories)
```

## Troubleshooting

### Hooks Not Firing

1. **Check hook configuration** in `.claude/settings.json`:
   ```bash
   grep -A 5 "hooks:" .claude/settings.json
   ```

2. **Verify hook script exists**:
   ```bash
   ls -la src/claude_mpm/scripts/claude-hook-fast.sh
   ```

3. **Check hook permissions**:
   ```bash
   stat -f "%A" src/claude_mpm/scripts/claude-hook-fast.sh
   ```

4. **Enable debug logging**:
   ```bash
   export CLAUDE_MPM_DEBUG_HOOKS=1
   ```

### Hook Execution Fails

Check logs at `~/.claude-mpm/logs/hooks.log`:

```bash
tail -f ~/.claude-mpm/logs/hooks.log
```

## Related Files

- **Hook Enum**: `src/claude_mpm/hooks/base_hook.py`
- **Hook Handler**: `src/claude_mpm/hooks/model_tier_hook.py`
- **Hook Dispatcher**: `src/claude_mpm/scripts/claude-hook-fast.sh`
- **Migration**: `src/claude_mpm/migrations/v6_3_2_hook_registration.py`
- **Settings Template**: `.claude/settings.json`

## Related Documentation

- [Hook System Architecture](../architecture/hooks.md)
- [Settings Configuration](./settings.md)
- [Startup Migrations](./startup-migrations.md)
