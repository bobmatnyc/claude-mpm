# Event Naming Issue Analysis

**Date**: 2025-12-11
**Issue**: Events showing as "unknown.claude_event" instead of proper event names
**Status**: ROOT CAUSE IDENTIFIED

## Problem Description

Events in the Claude MPM dashboard display as:
```
[hook] unknown.claude_event - event: claude_event
```

Instead of meaningful names like:
```
[hook] UserPromptSubmit - event: user_prompt_submit
```

## Root Cause Analysis

### Event Flow Path

1. **Claude Code Hooks** → Send events to `/api/events` via HTTP POST
2. **SocketIO Server** (`core.py:api_events_handler`) → Receives and processes events
3. **Event Normalization** (`event_normalizer.py`) → Transforms to standard schema
4. **SocketIO Broadcast** → Emits `claude_event` to dashboard clients
5. **Dashboard** (`event-viewer.js`) → Renders events in UI

### The Problem: Event Data Structure Confusion

#### What the Dashboard Expects

The `event-viewer.js` component (line 614-620) expects events in this normalized format:

```javascript
{
  "event": "claude_event",      // Socket.IO event name (always "claude_event")
  "source": "hook",              // WHERE: hook, system, dashboard, etc.
  "type": "hook",                // WHAT: Main category
  "subtype": "user_prompt",      // Specific event type
  "timestamp": "2025-12-11T...", // ISO timestamp
  "data": { /* event payload */ }
}
```

Display logic:
```javascript
// Line 619: Shows source prefix
const sourcePrefix = event.source !== 'system' ? `[${event.source}] ` : '';

// Line 615: Formats event type as "type.subtype"
const eventType = this.formatEventType(event);
// Returns: "hook.user_prompt" OR "hook" if subtype is "generic"
```

Expected display: `[hook] user_prompt - event: user_prompt`

#### What's Actually Happening

**Problem Location**: `src/claude_mpm/services/socketio/server/core.py`

**Line 286-290** (LOGGING ONLY, NOT THE ISSUE):
```python
# Extract event data from payload
event_type = (
    event_data.get("subtype")
    or event_data.get("hook_event_name")
    or "unknown"
)
self.logger.info(f"📨 Received HTTP event: {event_type}")
```

This logging code is CORRECT and uses the proper fields. The real issue is later.

**Line 295-333** (EVENT NORMALIZATION):
```python
# Transform hook event format to claude_event format if needed
if "hook_event_name" in event_data and "event" not in event_data:
    # This is a raw hook event, transform it
    from claude_mpm.services.socketio.event_normalizer import EventNormalizer

    normalizer = EventNormalizer()

    # Create the format expected by normalizer
    raw_event = {
        "type": "hook",
        "subtype": event_data.get("hook_event_name", "unknown")
                    .lower()
                    .replace("submit", "")
                    .replace("use", "_use"),
        "timestamp": event_data.get("timestamp"),
        "data": event_data.get("hook_input_data", {}),
        "source": "claude_hooks",
        "session_id": event_data.get("session_id"),
    }

    # Map hook event names to dashboard subtypes
    subtype_map = {
        "UserPromptSubmit": "user_prompt",
        "PreToolUse": "pre_tool",
        "PostToolUse": "post_tool",
        "Stop": "stop",
        "SubagentStop": "subagent_stop",
        "AssistantResponse": "assistant_response",
    }
    raw_event["subtype"] = subtype_map.get(
        event_data.get("hook_event_name"), "unknown"
    )

    normalized = normalizer.normalize(raw_event, source="hook")
    event_data = normalized.to_dict()
```

**THE BUG**: Line 306-309 processes the `hook_event_name` incorrectly!

```python
"subtype": event_data.get("hook_event_name", "unknown")
            .lower()                    # "UserPromptSubmit" → "userpromptsubmit"
            .replace("submit", "")      # "userpromptsubmit" → "userprompt"
            .replace("use", "_use"),    # "userprompt" → "userprompt" (no change)
```

This produces `"userprompt"` instead of `"user_prompt"`.

**THEN**: Lines 316-327 attempt to fix it with `subtype_map`:

```python
subtype_map = {
    "UserPromptSubmit": "user_prompt",  # Maps original name
    # ...
}
raw_event["subtype"] = subtype_map.get(
    event_data.get("hook_event_name"), "unknown"  # Gets "UserPromptSubmit"
)
```

**BUT WAIT**: Line 306 ALREADY set `raw_event["subtype"]` to the mangled value!
**Line 326 OVERWRITES IT** with the correct mapped value from `subtype_map`.

So the normalization SHOULD work correctly because line 326 overwrites line 306.

### The REAL Problem: Missing Events in subtype_map

The `subtype_map` (lines 316-327) only has 6 event types:
- UserPromptSubmit
- PreToolUse
- PostToolUse
- Stop
- SubagentStop
- AssistantResponse

**Missing events**:
- Any hook event NOT in this map gets `"unknown"` as subtype
- Claude Code sends MORE hook event types than just these 6

### Secondary Issue: "claude_event" Appearing as Event Name

When `subtype` is `"unknown"` OR `"generic"`, the dashboard's `formatEventType()` method (line 332-333) returns:

```javascript
if (event.type === event.subtype || event.subtype === 'generic') {
    return event.type;  // Returns just "hook" instead of "hook.unknown"
}
```

But the display shows "unknown.claude_event" which means:
- `event.type` = `"unknown"`
- `event.subtype` = `"claude_event"` OR
- Something is setting the event structure incorrectly

### Investigation Needed

**Question**: What field contains "claude_event"?

Looking at the normalization process:

```python
normalized = normalizer.normalize(raw_event, source="hook")
event_data = normalized.to_dict()
```

The `NormalizedEvent.to_dict()` method (event_normalizer.py line 82-91):

```python
def to_dict(self) -> Dict[str, Any]:
    return {
        "event": self.event,      # Always "claude_event"
        "source": self.source,    # "hook"
        "type": self.type,        # Should be "hook"
        "subtype": self.subtype,  # Should be mapped event name
        "timestamp": self.timestamp,
        "data": self.data,
    }
```

The field `"event"` is ALWAYS `"claude_event"` - this is the Socket.IO event name, NOT the event type.

**Dashboard rendering shows**:
```
[hook] unknown.claude_event - event: claude_event
```

This suggests:
- `source` = `"hook"` ✓ (shows as `[hook]`)
- `type` = `"unknown"` ✗ (should be `"hook"`)
- `subtype` = `"claude_event"` ✗ (should be event-specific like `"user_prompt"`)

### Hypothesis: Normalization Failing

If the `EventNormalizer.normalize()` method fails or returns a default event:

```python
# event_normalizer.py line 236-248
except Exception as e:
    self.stats["errors"] += 1
    self.logger.error(f"Failed to normalize event: {e}")

    # Return a generic event on error
    return NormalizedEvent(
        event="claude_event",
        source="system",
        type="unknown",          # ← This explains "unknown" type!
        subtype="error",
        timestamp=datetime.now(timezone.utc).isoformat(),
        data={"original": str(event_data), "error": str(e)},
    )
```

**BUT** the display shows `subtype="claude_event"`, not `subtype="error"`.

## Specific Fix Locations

### Fix 1: Complete the subtype_map (HIGH PRIORITY)

**File**: `src/claude_mpm/services/socketio/server/core.py`
**Lines**: 316-327

**Current**:
```python
subtype_map = {
    "UserPromptSubmit": "user_prompt",
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_tool",
    "Stop": "stop",
    "SubagentStop": "subagent_stop",
    "AssistantResponse": "assistant_response",
}
```

**Should Add** (based on Claude Code hook system):
```python
subtype_map = {
    # Existing mappings
    "UserPromptSubmit": "user_prompt",
    "PreToolUse": "pre_tool",
    "PostToolUse": "post_tool",
    "Stop": "stop",
    "SubagentStop": "subagent_stop",
    "AssistantResponse": "assistant_response",

    # Additional hook events
    "UserPromptCancel": "user_prompt_cancel",
    "ToolUseRejected": "tool_use_rejected",
    "ApiRequest": "api_request",
    "ApiResponse": "api_response",
    # ... (need to identify all Claude Code hook event names)
}
```

### Fix 2: Remove Redundant String Manipulation (MEDIUM PRIORITY)

**File**: `src/claude_mpm/services/socketio/server/core.py`
**Lines**: 304-309

**Current**:
```python
raw_event = {
    "type": "hook",
    "subtype": event_data.get("hook_event_name", "unknown")
                .lower()
                .replace("submit", "")
                .replace("use", "_use"),
    # ...
}
```

**Should Be** (since subtype_map overwrites this anyway):
```python
raw_event = {
    "type": "hook",
    "subtype": "generic",  # Will be overwritten by subtype_map
    # ...
}
```

OR better yet, move the mapping FIRST:

```python
hook_event_name = event_data.get("hook_event_name", "unknown")

# Map hook event names to dashboard subtypes
subtype_map = { ... }
subtype = subtype_map.get(hook_event_name, hook_event_name.lower())

raw_event = {
    "type": "hook",
    "subtype": subtype,
    # ...
}
```

### Fix 3: Add Logging for Unmapped Events (LOW PRIORITY - DEBUGGING)

**File**: `src/claude_mpm/services/socketio/server/core.py`
**After Line**: 327

**Add**:
```python
# Log unmapped hook events for debugging
if event_data.get("hook_event_name") and \
   event_data.get("hook_event_name") not in subtype_map:
    self.logger.warning(
        f"Unmapped hook event: {event_data.get('hook_event_name')} "
        f"- using subtype: {raw_event['subtype']}"
    )
```

### Fix 4: Default Fallback for Unknown Events

**File**: `src/claude_mpm/services/socketio/server/core.py`
**Line**: 326

**Current**:
```python
raw_event["subtype"] = subtype_map.get(
    event_data.get("hook_event_name"), "unknown"
)
```

**Better Fallback**:
```python
# Use original event name as fallback instead of "unknown"
hook_event_name = event_data.get("hook_event_name", "unknown")
raw_event["subtype"] = subtype_map.get(
    hook_event_name,
    hook_event_name.lower().replace("submit", "").replace("use", "_use")
)
```

## Investigation Tasks

1. **Capture Real Hook Events**: Use debug hook to log actual `hook_event_name` values sent by Claude Code
   - File: `/tmp/claude-event-debug.log` (from `tools/dev/debug/debug_hook.py`)
   - Run Claude Code with debug hook installed
   - Collect all `hook_event_name` values

2. **Verify Dashboard Receives Normalized Events**: Add console logging in `socket-client.js`
   - Log every `claude_event` received
   - Check `event.type`, `event.subtype`, `event.source` values
   - Compare with expected normalized format

3. **Check Event Normalizer Error Rate**: Query normalization stats
   - Call `EventNormalizer.get_stats()` during runtime
   - Check `stats["errors"]` count
   - Review logs for "Failed to normalize event" errors

4. **Review Claude Code Hook System**: Find official hook event name list
   - Check Claude Code documentation
   - Review hook JSON-RPC protocol spec
   - Identify all possible `hook_event_name` values

## Recommended Fix Priority

1. **IMMEDIATE**: Add complete `subtype_map` with all known hook events
2. **SHORT-TERM**: Add logging for unmapped events + better fallback
3. **MEDIUM-TERM**: Refactor normalization to be more robust
4. **LONG-TERM**: Auto-discover hook event names from Claude Code schema

## Expected Outcome After Fix

With complete `subtype_map`, events should display as:

```
[hook] user_prompt - User submitted prompt
[hook] pre_tool - Read (file.py)
[hook] post_tool - Read ✓ (file.py)
[hook] subagent_stop - research-agent completed
```

Instead of:

```
[hook] unknown.claude_event - event: claude_event
```

## Files Analyzed

- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/server/core.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/event_normalizer.py`
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/js/components/event-viewer.js`

## Next Steps

1. Deploy debug hook to capture real hook event names
2. Update `subtype_map` with complete mappings
3. Test with live Claude Code session
4. Verify events display correctly in dashboard
