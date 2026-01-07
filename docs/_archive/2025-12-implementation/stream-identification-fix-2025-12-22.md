# Stream Identification Fix - Dashboard Not Showing Current Session Events

**Date:** 2025-12-22
**Issue:** Monitor dashboard shows stream `e714e959-c788-4739-b87f-4b833c355d52` but doesn't display events from current claude-mpm project session.

## Root Cause

Hooks are globally configured in `~/.claude/settings.json` but **NOT activated** for the current project directory (`/Users/masa/Projects/claude-mpm`). Without project-specific hooks:

1. Claude Code doesn't send hook events with `session_id`
2. Events lack project context (`working_directory`, `git_branch`)
3. Dashboard can't group events by project/session
4. Events appear under generic UUID stream instead of project path

## Architecture Analysis

### Stream Identification Flow

```
Claude Code Hook Event
    ↓ (contains session_id from Claude)
Hook Handler (hook_handler.py)
    ↓ (extracts session_id, working_dir)
ConnectionManagerService (connection_manager.py)
    ↓ (wraps in event with session_id)
Socket.IO Server (server.py)
    ↓ (emits claude_event)
Dashboard Store (socket.svelte.ts)
    ↓ (calls getStreamId())
Stream Grouping
    ↓
Display by Project
```

### Key Code Locations

**1. Stream ID Extraction** (`src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts:58-67`):
```typescript
function getStreamId(event: ClaudeEvent): string | null {
    return (
        event.session_id ||              // ← PRIMARY SOURCE
        event.sessionId ||
        (event.data as any)?.session_id ||
        (event.data as any)?.sessionId ||
        event.source ||
        null
    );
}
```

**2. Event Emission** (`src/claude_mpm/hooks/claude_hooks/services/connection_manager.py:119-129`):
```python
raw_event = {
    "type": "hook",
    "subtype": event,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "data": data,
    "source": "claude_hooks",
    "session_id": data.get("sessionId"),  # ← FROM CLAUDE CODE
    "correlation_id": tool_call_id,
}
```

**3. Hook Event Processing** (`src/claude_mpm/hooks/claude_hooks/event_handlers.py:70-82`):
```python
# Extract comprehensive prompt data
prompt_data = {
    "prompt_text": prompt,
    "session_id": event.get("session_id", ""),  # ← REQUIRED
    "working_directory": working_dir,           # ← PROJECT PATH
    "git_branch": git_branch,                   # ← PROJECT CONTEXT
    # ...
}
```

### What's Missing

**Current State:**
```bash
# Project hooks NOT installed
$ ls .claude/hooks/
ls: .claude/hooks/: No such file or directory

$ cat .claude/hooks.json
cat: .claude/hooks.json: No such file or directory
```

**Expected State:**
```bash
# Project hooks SHOULD exist
$ ls .claude/hooks/
(empty or contains project-specific hooks)

$ cat .claude/hooks.json
{
  "hooks": {
    "PreToolUse": [...],
    "PostToolUse": [...],
    ...
  }
}
```

## Fix Implementation

### Option 1: Install Hooks for Current Project (Recommended)

**Steps:**
```bash
# Install hooks for current project
cd /Users/masa/Projects/claude-mpm
claude-mpm hooks install

# Verify installation
claude-mpm hooks status

# Restart Claude Code session
# (Close and reopen Claude Code OR run /mpm restart)
```

**Expected Output:**
```
✓ Hooks installed successfully for project: /Users/masa/Projects/claude-mpm
✓ Hook configuration written to: .claude/hooks.json
✓ Claude Code will send events with session_id on next session
```

### Option 2: Enable Global Hook Detection

**Alternative approach** - Make hooks detect project path without requiring `.claude/` directory:

**File:** `src/claude_mpm/hooks/claude_hooks/event_handlers.py`

```python
def handle_user_prompt_fast(self, event):
    # Get working directory from Claude Code event
    working_dir = event.get("cwd", os.getcwd())  # ← USE CWD FROM EVENT

    # Extract session_id (provided by Claude Code)
    session_id = event.get("session_id", str(uuid.uuid4()))  # ← FALLBACK TO UUID

    prompt_data = {
        "session_id": session_id,
        "working_directory": working_dir,
        "project_path": working_dir,  # ← ADD EXPLICIT PROJECT PATH
        # ...
    }
```

**Benefits:**
- No need for project-specific hook installation
- Works automatically for all Claude Code sessions
- Uses `cwd` from Claude Code hook event

**Trade-offs:**
- Requires Claude Code to send `cwd` in hook events (check compatibility)
- UUID fallback if `session_id` missing

### Option 3: Dashboard Fallback to Socket.IO Session

**Enhance dashboard to use Socket.IO session when no `session_id` available:**

**File:** `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts`

```typescript
function getStreamId(event: ClaudeEvent, socketSid?: string): string | null {
    // Try event session_id first
    const eventSessionId =
        event.session_id ||
        event.sessionId ||
        (event.data as any)?.session_id ||
        (event.data as any)?.sessionId;

    if (eventSessionId) return eventSessionId;

    // Fallback: Use working_directory as stream ID
    const workingDir =
        (event.data as any)?.working_directory ||
        (event.data as any)?.workingDirectory;

    if (workingDir) return workingDir;  // ← PROJECT PATH AS STREAM ID

    // Last resort: Socket.IO session
    return socketSid || event.source || null;
}
```

## Recommended Solution

**Immediate Fix:** Install hooks for current project:
```bash
cd /Users/masa/Projects/claude-mpm
claude-mpm hooks install
# Restart Claude Code session
```

**Long-term Improvement:** Implement Option 2 (global hook detection) to eliminate need for per-project hook installation.

## Verification Steps

After implementing fix:

1. **Check Hook Installation:**
   ```bash
   claude-mpm hooks status
   # Should show: ✓ Hooks installed for /Users/masa/Projects/claude-mpm
   ```

2. **Restart Claude Code Session:**
   - Close Claude Code
   - Reopen in `/Users/masa/Projects/claude-mpm`
   - OR run `/mpm restart` command

3. **Verify Stream Appears:**
   - Open dashboard: http://localhost:8765
   - Look for stream with project path: `/Users/masa/Projects/claude-mpm`
   - Should auto-select this stream

4. **Verify Events Appear:**
   - Run a command in Claude Code
   - Check dashboard Events tab
   - Should see events under current project stream

5. **Check Browser Console:**
   ```javascript
   // Should log:
   // [Cache] Found 1 cached streams
   // Socket store: Auto-selecting first stream: /Users/masa/Projects/claude-mpm
   // Socket store: Added event, total events: 1
   ```

## Related Files

- `src/claude_mpm/hooks/claude_hooks/installer.py` - Hook installation logic
- `src/claude_mpm/hooks/claude_hooks/hook_handler.py` - Hook event processing
- `src/claude_mpm/hooks/claude_hooks/event_handlers.py` - Event data extraction
- `src/claude_mpm/hooks/claude_hooks/services/connection_manager.py` - Event emission
- `src/claude_mpm/dashboard-svelte/src/lib/stores/socket.svelte.ts` - Stream identification
- `src/claude_mpm/services/monitor/server.py` - Socket.IO server

## Testing Commands

```bash
# Install hooks
claude-mpm hooks install

# Verify hooks
claude-mpm hooks status

# Check hook configuration
cat ~/.claude/settings.json | jq '.hooks'

# Monitor hook events (debug mode)
export CLAUDE_MPM_HOOK_DEBUG=true
tail -f /tmp/claude-mpm-hook.log

# Check dashboard streams
# Browser console: localStorage.getItem('claude-events-cache-<stream-id>')
```

## Success Criteria

✓ Dashboard shows stream with project path: `/Users/masa/Projects/claude-mpm`
✓ Events from current session appear in dashboard
✓ Stream auto-selected on dashboard load
✓ Events include `session_id`, `working_directory`, `git_branch`
✓ No more UUID-only streams for current project

## Prevention

**Add to project documentation:**

> **New Project Setup:**
> When starting work in a new project directory, run:
> ```bash
> claude-mpm hooks install
> ```
> This ensures the dashboard can track events and associate them with the correct project.

**Add to CI/CD:**

> **Pre-commit hook:**
> Verify hooks are installed before committing:
> ```bash
> #!/bin/bash
> if [ ! -f .claude/hooks.json ]; then
>     echo "Warning: Claude MPM hooks not installed for this project"
>     echo "Run: claude-mpm hooks install"
> fi
> ```
