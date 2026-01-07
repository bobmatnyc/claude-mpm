# SubagentStart Event Handling Analysis

**Date:** 2026-01-06
**Investigator:** Research Agent
**Issue:** Dashboard's Agents view conflating multiple engineers and missing research agent

## Problem Summary

The dashboard's Agents view is:
1. Conflating multiple engineer agents into one node
2. Missing the research agent entirely
3. Events received show 3 distinct agents but dashboard only shows PM + 1 Engineer

### Events Received:
```
subagent_start - engineer - 11:57:54 AM
subagent_start - research - 12:12:10 PM
subagent_start - engineer - 12:15:59 PM
```

### Dashboard Display:
- PM with 1 sub-agent
- Engineer (one node) - missing research and second engineer

## Root Cause Analysis

### SESSION_ID_SOURCE

Session IDs come from Claude Code's hook events (`event.get("session_id", "")`).

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:868`

```python
def handle_session_start_fast(self, event):
    session_id = event.get("session_id", "")
    # ...
```

### POTENTIAL_ISSUES

#### **ISSUE 1: Incorrect Event Routing** ⚠️ CRITICAL

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py:422`

```python
event_handlers = {
    # ...
    "SubagentStart": self.event_handlers.handle_session_start_fast,  # WRONG!
    "SessionStart": self.event_handlers.handle_session_start_fast,
    # ...
}
```

**Problem:** SubagentStart events are routed to the SAME handler as SessionStart events, which doesn't handle agent-specific information.

#### **ISSUE 2: Missing Agent Type Information** ⚠️ CRITICAL

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:872-878`

```python
session_start_data = {
    "session_id": session_id,
    "working_directory": working_dir,
    "git_branch": git_branch,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "hook_event_name": "SessionStart",  # Forces to SessionStart
}
# NO agent_type field!
```

**Problem:** The data emitted for SubagentStart events does NOT include `agent_type`, which is required by the frontend.

#### **ISSUE 3: Forced Event Name** ⚠️ CRITICAL

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:877,888`

```python
"hook_event_name": "SessionStart",  # Line 877 - Hardcoded!

self.hook_handler._emit_socketio_event("", "session_start", session_start_data)  # Line 888
```

**Problem:**
1. `hook_event_name` is hardcoded to "SessionStart" instead of preserving the original event type
2. Event is emitted as `"session_start"` instead of `"subagent_start"`

### Frontend Expectations

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/stores/agents.svelte.ts:413-425`

```typescript
// Handle subagent lifecycle events
if (event.subtype === 'subagent_start') {  // Line 413 - expects 'subagent_start'
    const agentType = getAgentType(event) || 'Agent';  // Line 414

    // Line 97-100: getAgentType implementation
    // Check data.agent_type directly (for subagent_start events)
    if (data.agent_type && typeof data.agent_type === 'string') {
        return data.agent_type;  // Expects data.agent_type!
    }
```

**Frontend Requirements:**
1. Event subtype must be `"subagent_start"` (not `"session_start"`)
2. Event data must include `agent_type` field
3. Event data must include `session_id` field

### Event Flow Comparison

#### **Expected Flow (What Should Happen):**

```
Claude Code
    ↓
SubagentStart Hook Event
    ↓
hook_handler.py (line 422)
    ↓
handle_subagent_start_fast()  [SHOULD EXIST]
    ↓
Emit: {
    subtype: "subagent_start",
    data: {
        agent_type: "engineer",  ✓
        session_id: "abc123...",  ✓
        ...
    }
}
    ↓
Frontend receives "subagent_start" with agent_type
    ↓
Creates unique agent node per session_id
```

#### **Actual Flow (What's Happening):**

```
Claude Code
    ↓
SubagentStart Hook Event
    ↓
hook_handler.py (line 422)
    ↓
handle_session_start_fast()  [WRONG HANDLER]
    ↓
Emit: {
    subtype: "session_start",  ✗ (should be "subagent_start")
    data: {
        session_id: "abc123...",  ✓
        // NO agent_type!  ✗
    }
}
    ↓
Frontend receives "session_start" without agent_type
    ↓
getAgentType() returns undefined or "Agent"
    ↓
Agents get conflated due to missing agent_type
```

### Why Conflation Happens

1. **All SubagentStart events → session_start events**
   - Frontend's `if (event.subtype === 'subagent_start')` check fails
   - Events are not processed as subagent events

2. **No agent_type in emitted data**
   - Even if frontend tried to process them, `getAgentType()` returns undefined
   - Agents can't be distinguished by type

3. **Potential session_id issues**
   - If session_ids are missing or reused, agents get further conflated
   - Without agent_type, session_id becomes the only identifier

## Comparison with Task Delegation Events

### Task Tool Delegation (WORKS CORRECTLY)

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:278-290`

```python
# Emit a subagent_start event for better tracking
subagent_start_data = {
    "agent_type": agent_type,              # ✓ agent_type included
    "agent_id": f"{agent_type}_{session_id}",
    "session_id": session_id,              # ✓ session_id included
    "prompt": tool_input.get("prompt", ""),
    "description": tool_input.get("description", ""),
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "hook_event_name": "SubagentStart",    # ✓ Correct hook_event_name
}
self.hook_handler._emit_socketio_event(
    "", "subagent_start", subagent_start_data  # ✓ Correct event name
)
```

**This works correctly!** It:
1. Includes `agent_type` ✓
2. Includes `session_id` ✓
3. Uses correct `hook_event_name` ✓
4. Emits as `"subagent_start"` ✓

### SubagentStart Hook Event (BROKEN)

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:872-888`

```python
session_start_data = {
    "session_id": session_id,               # ✓ session_id included
    "working_directory": working_dir,
    "git_branch": git_branch,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "hook_event_name": "SessionStart",      # ✗ WRONG! Should be "SubagentStart"
    # NO agent_type!                        # ✗ MISSING!
}
self.hook_handler._emit_socketio_event("", "session_start", session_start_data)
                                        # ✗ WRONG! Should be "subagent_start"
```

**This is broken!** It:
1. Missing `agent_type` ✗
2. Wrong `hook_event_name` ✗
3. Wrong event name in emit ✗

## FIX_LOCATION

**Primary Fix:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py`

### Lines Requiring Changes:

1. **Create new handler (recommended):** Add new method after line 859
2. **Fix event routing:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py:422`
3. **Extract agent_type:** Must get agent_type from SubagentStart event

## RECOMMENDED_FIX

### Option 1: Create Dedicated SubagentStart Handler (RECOMMENDED)

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py`

Add new method after `handle_session_start_fast`:

```python
def handle_subagent_start_fast(self, event):
    """Handle subagent start events with agent type information.

    WHY separate handler:
    - SubagentStart events include agent_type information
    - SessionStart events do not have agent_type
    - Frontend requires agent_type for proper agent visualization
    - Must preserve SubagentStart event type for frontend routing
    """
    session_id = event.get("session_id", "")
    working_dir = event.get("cwd", "")
    git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

    # Extract agent_type from the event
    agent_type = event.get("agent_type", "Agent")

    # Normalize agent type if needed
    try:
        from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
        normalizer = AgentNameNormalizer()
        agent_type = normalizer.to_task_format(agent_type) if agent_type != "Agent" else "Agent"
    except ImportError:
        # Fallback normalization
        agent_type = agent_type.lower().replace("_", "-")

    subagent_start_data = {
        "agent_type": agent_type,                    # REQUIRED by frontend
        "agent_id": f"{agent_type}_{session_id}",
        "session_id": session_id,
        "working_directory": working_dir,
        "git_branch": git_branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hook_event_name": "SubagentStart",          # Preserve original event type
    }

    # Debug logging
    if DEBUG:
        print(
            f"Hook handler: Processing SubagentStart - agent: '{agent_type}', session: '{session_id}'",
            file=sys.stderr,
        )

    # Emit with correct event name
    self.hook_handler._emit_socketio_event("", "subagent_start", subagent_start_data)
```

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py:422`

Update event routing:

```python
event_handlers = {
    # ...
    "SubagentStop": self.event_handlers.handle_subagent_stop_fast,
    "SubagentStart": self.event_handlers.handle_subagent_start_fast,  # NEW HANDLER
    "SessionStart": self.event_handlers.handle_session_start_fast,
    # ...
}
```

### Option 2: Modify Existing Handler (SIMPLER BUT LESS CLEAN)

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:860-889`

Modify `handle_session_start_fast` to detect SubagentStart events:

```python
def handle_session_start_fast(self, event):
    """Handle session start events (SessionStart and SubagentStart).

    WHY handle both:
    - SessionStart: Generic session initialization
    - SubagentStart: Agent-specific session with agent_type
    """
    session_id = event.get("session_id", "")
    working_dir = event.get("cwd", "")
    git_branch = self._get_git_branch(working_dir) if working_dir else "Unknown"

    # Detect if this is a SubagentStart event
    hook_event_name = event.get("hook_event_name", "SessionStart")
    is_subagent = hook_event_name == "SubagentStart"

    session_start_data = {
        "session_id": session_id,
        "working_directory": working_dir,
        "git_branch": git_branch,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hook_event_name": hook_event_name,  # Preserve original event type
    }

    # Add agent_type for SubagentStart events
    if is_subagent:
        agent_type = event.get("agent_type", "Agent")

        # Normalize agent type
        try:
            from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
            normalizer = AgentNameNormalizer()
            agent_type = normalizer.to_task_format(agent_type)
        except ImportError:
            agent_type = agent_type.lower().replace("_", "-")

        session_start_data["agent_type"] = agent_type
        session_start_data["agent_id"] = f"{agent_type}_{session_id}"

    # Debug logging
    if DEBUG:
        event_type = "SubagentStart" if is_subagent else "SessionStart"
        agent_info = f", agent: '{session_start_data.get('agent_type')}'" if is_subagent else ""
        print(
            f"Hook handler: Processing {event_type} - session: '{session_id}'{agent_info}",
            file=sys.stderr,
        )

    # Emit with correct event name based on type
    event_name = "subagent_start" if is_subagent else "session_start"
    self.hook_handler._emit_socketio_event("", event_name, session_start_data)
```

## Testing Verification

### Before Fix (Expected Logs):
```
Hook handler: Processing SessionStart - session: 'abc123...'
Hook handler: Processing SessionStart - session: 'def456...'
Hook handler: Processing SessionStart - session: 'ghi789...'
```

### After Fix (Expected Logs):
```
Hook handler: Processing SubagentStart - agent: 'engineer', session: 'abc123...'
Hook handler: Processing SubagentStart - agent: 'research', session: 'def456...'
Hook handler: Processing SubagentStart - agent: 'engineer', session: 'ghi789...'
```

### Frontend Verification:

Check browser console for these logs:

```javascript
[AgentsStore] subagent_start detected: {
    sessionId: "abc123...",
    agentType: "engineer",
    timestamp: "11:57:54 AM",
    hasSessionId: true
}

[AgentsStore] subagent_start detected: {
    sessionId: "def456...",
    agentType: "research",
    timestamp: "12:12:10 PM",
    hasSessionId: true
}

[AgentsStore] subagent_start detected: {
    sessionId: "ghi789...",
    agentType: "engineer",
    timestamp: "12:15:59 PM",
    hasSessionId: true
}
```

## Additional Considerations

### Session ID Uniqueness

Verify that each SubagentStart event has a unique session_id:

```python
# In hook handler debug output
print(f"SubagentStart session_id: {session_id}")
```

Expected: Each subagent delegation should have a unique session_id from Claude Code.

### Agent Type Extraction

SubagentStart events from Claude Code should include agent_type. Verify in debug logs:

```python
# In handle_subagent_start_fast
print(f"Event keys: {list(event.keys())}")
print(f"agent_type: {event.get('agent_type')}")
```

If `agent_type` is missing from the raw event, we need to investigate Claude Code's hook event format.

## Summary

**Root Cause:** SubagentStart events are incorrectly routed to `handle_session_start_fast`, which:
1. Does not include `agent_type` in emitted data
2. Forces `hook_event_name` to "SessionStart"
3. Emits as `"session_start"` instead of `"subagent_start"`

**Impact:** Frontend cannot distinguish between different agent types, causing conflation.

**Solution:** Create dedicated `handle_subagent_start_fast` handler that preserves agent information and emits correct event type.

**Priority:** HIGH - This breaks agent visualization in the dashboard.

**Estimated Fix Time:** 15-30 minutes
