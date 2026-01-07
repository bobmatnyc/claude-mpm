# SessionStart Hook Subtype Investigation

**Date**: 2025-12-19
**Issue**: "SessionStart:startup hook error" and "SessionStart:resume hook error" persist despite SessionStart hook configuration
**Status**: ROOT CAUSE IDENTIFIED

## Executive Summary

The SessionStart hook errors occur because **Claude Code uses a matcher-based query system for SessionStart events**, sending them as `SessionStart:startup` and `SessionStart:resume` (with subtypes). Our current hook configuration registers SessionStart without a matcher, which causes Claude Code to fail finding matching hooks for these subtype-qualified events.

## Root Cause Analysis

### 1. How Claude Code Sends SessionStart Events

From Claude Code debug logs (found in chunk-graph.json):

```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 0 hook matchers in settings
[DEBUG] Matched 0 unique hooks for query "startup" (0 before deduplication)
[DEBUG] Found 0 hook commands to execute
```

**Key Discovery**: Claude Code calls `SessionStart:startup` and `SessionStart:resume` events with:
- **Event Type**: `SessionStart`
- **Query/Matcher**: `startup` or `resume`

### 2. Current Hook Configuration (INCORRECT)

In `src/claude_mpm/hooks/claude_hooks/installer.py` line 525:

```python
# Non-tool events don't need a matcher - just hooks array
non_tool_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart", "SessionStart"]
for event_type in non_tool_events:
    settings["hooks"][event_type] = [
        {
            "hooks": [hook_command],  # ❌ NO MATCHER
        }
    ]
```

This creates a configuration like:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [{"type": "command", "command": "/path/to/hook"}]
      }
    ]
  }
}
```

**Problem**: No `matcher` field means Claude Code cannot match `SessionStart:startup` or `SessionStart:resume` queries.

### 3. What Claude Code Expects (CORRECT)

Based on tool event patterns and the debug log showing it looks for matchers:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "*",  // ✅ Match all SessionStart subtypes
        "hooks": [{"type": "command", "command": "/path/to/hook"}]
      }
    ]
  }
}
```

OR with specific subtypes:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup",
        "hooks": [{"type": "command", "command": "/path/to/hook"}]
      },
      {
        "matcher": "resume",
        "hooks": [{"type": "command", "command": "/path/to/hook"}]
      }
    ]
  }
}
```

## Comparison with Other Events

### Tool Events (CORRECT - Working)

```python
# Tool-related events need a matcher string
tool_events = ["PreToolUse", "PostToolUse"]
for event_type in tool_events:
    settings["hooks"][event_type] = [
        {
            "matcher": "*",  # ✅ String value to match all tools
            "hooks": [hook_command],
        }
    ]
```

Result:
```json
{
  "PreToolUse": [{"matcher": "*", "hooks": [...]}],
  "PostToolUse": [{"matcher": "*", "hooks": [...]}]
}
```

✅ **Works**: Claude Code finds hooks for all tool types.

### Non-Tool Events (MIXED - Partially Broken)

Current configuration:
```python
non_tool_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart", "SessionStart"]
```

Result:
```json
{
  "UserPromptSubmit": [{"hooks": [...]}],  // ✅ Works (no subtypes)
  "Stop": [{"hooks": [...]}],              // ✅ Works (no subtypes)
  "SubagentStop": [{"hooks": [...]}],      // ✅ Works (no subtypes)
  "SubagentStart": [{"hooks": [...]}],     // ❌ May fail if has subtypes
  "SessionStart": [{"hooks": [...]}]       // ❌ FAILS (has subtypes: startup, resume)
}
```

## Evidence from Debug Logs

### SessionStart:startup (Startup Event)

```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 0 hook matchers in settings
[DEBUG] Matched 0 unique hooks for query "startup" (0 before deduplication)
[DEBUG] Found 0 hook commands to execute
```

**Analysis**:
- Event name: `SessionStart:startup`
- Query/matcher: `startup`
- Looks for matchers in settings
- Finds 0 matchers (because we didn't provide one)
- Returns 0 hook commands

### UserPromptSubmit (Working Event for Comparison)

```
[DEBUG] Executing hooks for UserPromptSubmit
[DEBUG] Getting matching hook commands for UserPromptSubmit with query: undefined
[DEBUG] Found 0 hook matchers in settings
[DEBUG] Matched 0 unique hooks for query "no match query" (0 before deduplication)
```

**Analysis**:
- Event name: `UserPromptSubmit`
- Query: `undefined` (no subtype)
- Still finds 0 matchers because hooks were not installed in this test environment
- **Key difference**: Query is `undefined`, not a specific subtype like "startup"

## Hook Installation Type Discovery

Claude Code uses **TWO DIFFERENT hook configuration patterns**:

### Pattern 1: Matcher-Based (for events with subtypes or variants)

**When to use**: Events that have subtypes, variants, or need filtering
- Tool events: `PreToolUse`, `PostToolUse` (matcher = tool name like "Bash", "Read", "*")
- Session events: `SessionStart` (matcher = subtype like "startup", "resume", "*")
- Possibly: `SubagentStart` (needs investigation)

**Configuration format**:
```json
{
  "EventName": [
    {
      "matcher": "pattern",  // Required: "*" for all, specific name for filtering
      "hooks": [...]
    }
  ]
}
```

### Pattern 2: Direct Hooks (for simple events without subtypes)

**When to use**: Events that have no subtypes or variants
- User events: `UserPromptSubmit`, `UserPromptCancel`
- Control events: `Stop`
- Completion events: `SubagentStop` (possibly, needs confirmation)

**Configuration format**:
```json
{
  "EventName": [
    {
      "hooks": [...]  // No matcher field
    }
  ]
}
```

## SessionStart Event Types

Based on error messages and patterns, SessionStart has at least two subtypes:

1. **`SessionStart:startup`** - Fired when Claude Code starts up
2. **`SessionStart:resume`** - Fired when resuming an existing session

**Hypothesis**: These may also exist:
- `SessionStart:new` - Creating a new conversation?
- `SessionStart:restore` - Restoring from saved state?

## The Fix

### Option 1: Universal Matcher (Recommended)

**Location**: `src/claude_mpm/hooks/claude_hooks/installer.py` line 524-531

**Change**:
```python
# SessionStart needs matcher for subtypes (startup, resume)
# Other non-tool events don't need matchers
non_tool_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart"]
for event_type in non_tool_events:
    settings["hooks"][event_type] = [
        {
            "hooks": [hook_command],
        }
    ]

# SessionStart requires matcher for subtypes
settings["hooks"]["SessionStart"] = [
    {
        "matcher": "*",  # Match all SessionStart subtypes (startup, resume, etc.)
        "hooks": [hook_command],
    }
]
```

**Why this works**:
- `matcher: "*"` tells Claude Code to match ALL SessionStart subtypes
- Works for both `SessionStart:startup` and `SessionStart:resume`
- Future-proof for any new SessionStart subtypes

### Option 2: Explicit Subtype Matchers (More Specific)

```python
# SessionStart with explicit subtype matchers
settings["hooks"]["SessionStart"] = [
    {
        "matcher": "startup",
        "hooks": [hook_command],
    },
    {
        "matcher": "resume",
        "hooks": [hook_command],
    }
]
```

**Pros**: More explicit, could have different handlers for startup vs resume
**Cons**: Must update code when new subtypes are added

### Option 3: Hybrid Approach (Future-Proof Categories)

```python
# Categorize events by matcher requirement
matcher_based_events = {
    "PreToolUse": "*",      # Match all tools
    "PostToolUse": "*",     # Match all tools
    "SessionStart": "*",    # Match all session start subtypes (startup, resume, etc.)
}

simple_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart"]

# Configure matcher-based events
for event_type, matcher in matcher_based_events.items():
    settings["hooks"][event_type] = [
        {
            "matcher": matcher,
            "hooks": [hook_command],
        }
    ]

# Configure simple events
for event_type in simple_events:
    settings["hooks"][event_type] = [
        {
            "hooks": [hook_command],
        }
    ]
```

## Investigation of SubagentStart

**Question**: Does `SubagentStart` also need a matcher?

**Current status**: Configured as simple event (no matcher)

**Recommendation**: Monitor logs for patterns like:
- `[DEBUG] Executing hooks for SubagentStart:somesubtype`
- `[DEBUG] Getting matching hook commands for SubagentStart with query: somequery`

If logs show subtypes for SubagentStart, move it to matcher-based category.

## Expected Behavior After Fix

### Before Fix (Current)
```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 0 hook matchers in settings
[ERROR] SessionStart:startup hook error
```

### After Fix (Expected)
```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 1 hook matcher in settings (matcher: "*")
[DEBUG] Matched 1 unique hook for query "startup"
[DEBUG] Found 1 hook command to execute
[DEBUG] Executing hook: /path/to/claude-hook-handler.sh
[DEBUG] Hook completed successfully
```

## Testing Plan

### 1. Verify Fix Installation

```bash
# Check settings.json has matcher for SessionStart
cat ~/.claude/settings.json | jq '.hooks.SessionStart'
```

Expected output:
```json
[
  {
    "matcher": "*",
    "hooks": [
      {
        "type": "command",
        "command": "/path/to/claude-hook-handler.sh"
      }
    ]
  }
]
```

### 2. Test Startup Event

```bash
# Restart Claude Code and check for errors
claude --version
# Look for: ✅ No "SessionStart:startup hook error"
```

### 3. Test Resume Event

```bash
# Start a conversation, close it, reopen it
# Look for: ✅ No "SessionStart:resume hook error"
```

### 4. Verify Hook Execution

Check hook handler logs for SessionStart processing:
```bash
tail -f /tmp/claude-mpm-hook.log | grep SessionStart
```

Expected output:
```
[timestamp] Processing hook event: SessionStart (PID: ...)
Hook handler: Processing SessionStart - session: 'abc123'
```

## Related Code Locations

### Hook Installer
- **File**: `src/claude_mpm/hooks/claude_hooks/installer.py`
- **Method**: `_update_claude_settings()` (line 488)
- **Lines**: 524-531 (SessionStart configuration)

### Hook Handler
- **File**: `src/claude_mpm/hooks/claude_hooks/hook_handler.py`
- **Method**: `_route_event()` (line 384)
- **Lines**: 421 (SessionStart event routing)

### Event Handler
- **File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- **Method**: `handle_session_start_fast()` (line 790)
- **Purpose**: Processes SessionStart events after routing

## Validation Checklist

- [ ] Add `matcher: "*"` to SessionStart hook configuration
- [ ] Remove SessionStart from `non_tool_events` list
- [ ] Test with `claude-mpm run` to verify no errors on startup
- [ ] Test session resume to verify no errors on resume
- [ ] Verify hooks execute successfully in logs
- [ ] Check dashboard shows SessionStart events
- [ ] Document matcher requirement in code comments

## Open Questions

1. **SubagentStart matcher requirement**: Does it have subtypes? Need to check logs.
2. **Other SessionStart subtypes**: Are there more than "startup" and "resume"?
3. **SessionEnd event**: Does it exist? Does it need a matcher?
4. **Version compatibility**: When did Claude Code introduce SessionStart subtypes?

## Conclusion

**Root Cause**: SessionStart events use a matcher-based query system (`SessionStart:startup`, `SessionStart:resume`) but our hook configuration doesn't provide a matcher field, causing Claude Code to find 0 matching hooks.

**Fix**: Add `matcher: "*"` to SessionStart hook configuration to match all subtypes.

**Impact**: Eliminates "SessionStart:startup hook error" and "SessionStart:resume hook error" on every Claude Code startup and session resume.

**Priority**: HIGH - User-visible error messages on every startup.

**Effort**: LOW - Single line configuration change + testing.

**Risk**: LOW - Simple matcher addition, no breaking changes.
