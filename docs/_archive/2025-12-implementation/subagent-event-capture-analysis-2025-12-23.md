# Sub-Agent Event Capture Analysis

**Date:** 2025-12-23
**Research Focus:** Why sub-agent events may not appear in the dashboard when `/mpm-organize` spawns `project-organizer` agent
**Status:** ✅ Complete

---

## Executive Summary

The claude-mpm hook system **IS DESIGNED** to capture sub-agent events including tool calls made by spawned agents like `project-organizer`. The architecture includes comprehensive tracking through:

1. **PreToolUse hooks** that detect Task delegations and track agent spawning
2. **SubagentStop hooks** that capture agent completion and results
3. **Cross-process correlation** using session IDs and correlation managers
4. **Direct Socket.IO emission** with HTTP fallback for reliability

**Potential Gap Identified:** While the architecture supports sub-agent tracking, there may be issues with:
- Session ID correlation between PM and sub-agents
- Event emission timing or buffering
- Dashboard filtering/display logic
- Claude Code version compatibility

---

## Architecture Analysis

### 1. Hook Installation & Configuration

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/installer.py`

The hooks are installed in Claude Code's `~/.claude/settings.json` file with matchers for:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "*", "hooks": [{"type": "command", "command": "/path/to/hook-wrapper.sh"}]}],
    "PostToolUse": [{"matcher": "*", "hooks": [...]}],
    "SubagentStop": [{"hooks": [...]}],
    "SubagentStart": [{"hooks": [...]}],
    "UserPromptSubmit": [{"matcher": "*", "hooks": [...]}],
    "SessionStart": [{"matcher": "*", "hooks": [...]}],
    "Stop": [{"hooks": [...]}]
  }
}
```

**Key Finding:** Hooks are configured for **ALL Claude Code sessions** including main and sub-agents. The `matcher: "*"` ensures all tool calls and events are captured.

**Version Requirements:**
- Minimum Claude Code version: `1.0.92` (for matcher-based hooks)
- PreToolUse input modification: `2.0.30+` (not required for event capture)

---

### 2. Event Flow Architecture

**Primary Path:** Hook Process → Connection Manager → Socket.IO → Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│ CLAUDE CODE SESSION (Main PM or Sub-Agent)                  │
├─────────────────────────────────────────────────────────────┤
│  1. Event occurs (Tool call, Prompt, Stop, etc.)            │
│  2. Claude Code triggers hook via settings.json             │
│  3. Spawns hook-wrapper.sh process                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ HOOK WRAPPER (Ephemeral Process)                            │
├─────────────────────────────────────────────────────────────┤
│  hook-wrapper.sh → hook_handler.py → Event Handlers         │
│                                                              │
│  • Parses event JSON from stdin                             │
│  • Routes to specialized handler (PreTool, SubagentStop)    │
│  • Extracts metadata (session_id, agent_type, tool_name)    │
│  • Stores correlation data (CorrelationManager)             │
│  • Tracks delegations (StateManagerService)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ CONNECTION MANAGER (Event Emission)                         │
├─────────────────────────────────────────────────────────────┤
│  • Normalizes event to mpm_event schema                     │
│  • Primary: Direct Socket.IO via connection pool            │
│  • Fallback: HTTP POST to localhost:8765/api/events         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ DASHBOARD SERVER (Socket.IO Receiver)                       │
├─────────────────────────────────────────────────────────────┤
│  • Receives mpm_event via Socket.IO                         │
│  • Broadcasts to connected frontend clients                 │
│  • Updates dashboard UI in real-time                        │
└─────────────────────────────────────────────────────────────┘
```

**Critical Insight:** Each Claude Code session (main PM or sub-agent) has **its own hook process** that independently emits events to the dashboard.

---

### 3. Sub-Agent Event Tracking

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py`

#### 3.1 Task Delegation Detection (PreToolUse)

When PM uses the Task tool to spawn a sub-agent:

```python
# Lines 189-290 in event_handlers.py
def handle_pre_tool_fast(self, event):
    if tool_name == "Task":
        # Extract agent type from tool_input
        agent_type = tool_input.get("subagent_type", "unknown")

        # Track delegation in StateManager
        self.hook_handler._track_delegation(session_id, agent_type, request_data)

        # Emit subagent_start event
        self._emit_socketio_event("", "subagent_start", {
            "agent_type": agent_type,
            "session_id": session_id,
            "prompt": tool_input.get("prompt"),
            "hook_event_name": "SubagentStart"
        })
```

**What Gets Tracked:**
- Agent type (research, engineer, qa, etc.)
- Session ID of the spawned agent
- Task prompt and description
- Timestamp and working directory

#### 3.2 Sub-Agent Tool Calls (PreToolUse/PostToolUse)

When a **sub-agent** makes tool calls (Read, Write, Bash, etc.), **the same hooks fire** because:
1. Sub-agent runs in its own Claude Code session
2. Hook configuration applies to ALL sessions
3. Each tool call triggers PreToolUse → PostToolUse hooks

**Example Flow:**
```
PM Session (session_id=ABC123):
  → PreToolUse: Task(subagent_type="project-organizer")
  → SubagentStart event emitted

Sub-Agent Session (session_id=XYZ789):  ← NEW SESSION
  → PreToolUse: Read(file_path="/path/to/file")
  → PostToolUse: Read (exit_code=0)
  → PreToolUse: Write(file_path="/output")
  → PostToolUse: Write (exit_code=0)
  → SubagentStop event emitted

PM Session (ABC123):
  → PostToolUse: Task (exit_code=0)
```

**Key Observation:** Sub-agent tool calls have **DIFFERENT session_id** from PM session.

#### 3.3 Sub-Agent Completion (SubagentStop)

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/subagent_processor.py`

When sub-agent completes:

```python
# Lines 36-122 in subagent_processor.py
def process_subagent_stop(self, event: dict):
    session_id = event.get("session_id")

    # Retrieve agent type from StateManager tracking
    agent_type = self.state_manager.get_delegation_agent_type(session_id)

    # Extract structured response from output
    structured_response = self._extract_structured_response(output, agent_type)

    # Emit subagent_stop event
    self.connection_manager.emit_event("/hook", "subagent_stop", {
        "agent_type": agent_type,
        "session_id": session_id,
        "reason": reason,
        "hook_event_name": "SubagentStop"
    })
```

**What Gets Captured:**
- Agent completion reason (completed, error, timeout)
- Structured JSON response (if present)
- Duration and exit code
- Working directory and git branch

---

### 4. Session Correlation

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/correlation_manager.py` (referenced)

The system uses:

1. **StateManagerService** - Tracks delegation requests by session ID
2. **CorrelationManager** - Stores tool_call_id for PreTool/PostTool correlation
3. **Fuzzy Matching** - Handles session ID truncation/mismatches

```python
# From subagent_processor.py lines 215-240
request_info = self.state_manager.find_matching_request(session_id)

# If exact match fails, try partial matching
if not request_info and session_id:
    for stored_sid in delegation_requests.keys():
        if stored_sid.startswith(session_id[:8]) or session_id.startswith(stored_sid[:8]):
            request_info = delegation_requests.get(stored_sid)
            break
```

**Potential Issue:** If PM session_id doesn't match sub-agent session_id in tracking data, correlation may fail.

---

### 5. Event Emission Path

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`

**Single-Path Architecture:**

```python
# Lines 106-187
def emit_event(self, namespace: str, event: str, data: dict):
    # Normalize event to mpm_event schema
    normalized_event = self.event_normalizer.normalize(raw_event, source="hook")
    claude_event_data = normalized_event.to_dict()

    # Primary: Direct Socket.IO
    if self.connection_pool:
        self.connection_pool.emit("mpm_event", claude_event_data)
        return  # Success

    # Fallback: HTTP POST
    self._try_http_fallback(claude_event_data)
```

**Critical Design:**
- Events go through **ONE path** (Socket.IO or HTTP)
- No duplicate events from multiple emission methods
- Fast ephemeral process (exits after emit)

**Debug Mode:** Set `CLAUDE_MPM_HOOK_DEBUG=true` to see emission logs in `/tmp/hook-wrapper.log`

---

## Potential Gaps & Issues

### Gap 1: Sub-Agent Session ID Tracking

**Issue:** When PM delegates to sub-agent via Task tool:
- PM PreToolUse captures `session_id=ABC123`
- Sub-agent runs in **new session** with `session_id=XYZ789`
- Sub-agent's tool calls emit events with `XYZ789`
- Dashboard may not correlate `XYZ789` back to PM session

**Evidence:**
```python
# event_handlers.py line 239
self.hook_handler._track_delegation(session_id, agent_type, request_data)
```
This stores delegation under PM's session_id, but sub-agent events come from **different session_id**.

**Recommendation:** Check if dashboard groups events by:
- Working directory (cwd)
- Parent/child session relationships
- Agent type classification

### Gap 2: Event Filtering in Dashboard

**Issue:** Dashboard may filter out certain event types or session IDs

**Files to Check:**
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/` - Frontend filtering logic
- Socket.IO event handlers - Backend routing/filtering
- Event normalizer - Schema validation that might drop events

**Recommendation:** Verify dashboard shows ALL `mpm_event` types including:
- `subtype: "pre_tool"` with `tool_name: "Read"`, `"Write"`, etc.
- `subtype: "post_tool"` with exit codes
- `session_id` from sub-agent (not just PM)

### Gap 3: Event Emission Timing

**Issue:** Sub-agent tool calls happen rapidly - events may be:
- Buffered and not flushed immediately
- Lost due to process exit before emission completes
- Dropped by Socket.IO if connection pool is full

**Evidence:**
```python
# connection_manager.py line 177
self.connection_pool.emit("mpm_event", claude_event_data)
return  # Success - no wait for ACK
```
Hook process exits immediately after emitting - no confirmation of delivery.

**Recommendation:**
- Check Socket.IO server logs for received events
- Verify `connection_pool.emit()` is non-blocking but reliable
- Add event queueing if sub-agents make 50+ tool calls quickly

### Gap 4: Duplicate Event Detection

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/duplicate_detector.py` (referenced)

**Issue:** Duplicate detector may incorrectly filter sub-agent events

```python
# hook_handler.py lines 284-294
if self.duplicate_detector.is_duplicate(event):
    if DEBUG:
        print(f"Skipping duplicate event: {event.get('hook_event_name')}")
    self._continue_execution()
    return
```

**Recommendation:** Verify duplicate detection uses:
- `session_id` + `timestamp` + `tool_name` as key
- Not just `tool_name` (which would filter multiple Read calls)
- Time window < 100ms (sub-agent may make similar calls > 100ms apart)

---

## Slash Command Handling

**File:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py` (lines 64-68)

```python
def handle_user_prompt_fast(self, event):
    prompt = event.get("prompt", "")

    # Skip /mpm commands to reduce noise unless debug is enabled
    if prompt.startswith("/mpm") and not DEBUG:
        return
```

**Finding:** `/mpm-organize` command is **SKIPPED** in non-debug mode to reduce noise.

**Implications:**
- The user prompt event for `/mpm-organize` won't appear in dashboard (unless DEBUG=true)
- However, the **Task delegation** and **SubagentStop** events are NOT skipped
- Sub-agent tool calls are also NOT skipped (different handler)

**Recommendation:** This is intentional filtering - not related to missing sub-agent events.

---

## Event Rate Limiting

**No evidence of rate limiting** in the hook handler or connection manager.

**Potential Issue:** If `project-organizer` makes 100+ tool calls:
- Socket.IO may buffer or drop events if client can't keep up
- HTTP fallback has 2-second timeout - may fail under load
- Dashboard frontend may lag rendering 100+ events

**Recommendation:**
- Check dashboard for event batching/virtualization
- Monitor Socket.IO queue depth during heavy sub-agent work
- Add event sampling for non-critical events (PreToolUse for Read can be sampled)

---

## Verification Steps

To diagnose why sub-agent events don't appear:

### 1. Enable Debug Logging

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

Then run `/mpm-organize` and check:
- `/tmp/hook-wrapper.log` - Hook invocations
- `/tmp/hook-error.log` - Hook errors
- `/tmp/claude-mpm-hook.log` - Smart hook fallback logs

Look for:
```
[timestamp] Processing hook event: PreToolUse (PID: xxxxx)
  - tool_name: Read
  - session_id: XYZ789...
[timestamp] ✅ Emitted via connection pool: pre_tool
```

### 2. Check Session ID Correlation

Add logging in `event_handlers.py`:

```python
# Around line 189 in handle_pre_tool_fast
if tool_name == "Task":
    print(f"Task delegation: PM session={session_id}, agent={agent_type}")

# In subagent_processor.py around line 70
print(f"SubagentStop: session={session_id}, agent={agent_type}")
print(f"  - Stored sessions: {list(self.state_manager.delegation_requests.keys())}")
```

Compare PM session_id with sub-agent session_id.

### 3. Verify Dashboard Receives Events

Check dashboard server logs for:
```
Received mpm_event: type=hook, subtype=pre_tool, tool_name=Read
Broadcasting to N clients
```

If events arrive at server but don't appear in UI → Frontend filtering issue.

If events don't arrive at server → Socket.IO or HTTP emission failure.

### 4. Test with Simple Sub-Agent

Create a minimal test:

```bash
# In Claude Code
/ask What is 2+2?
# This spawns a simple agent with minimal tool calls

# Check if those events appear in dashboard
```

If simple agents work but `project-organizer` doesn't → Scale/complexity issue.

### 5. Check Claude Code Version

```bash
claude --version
```

Must be >= 1.0.92 for matcher-based hooks.

If older → Hooks won't fire for sub-agents.

---

## Dashboard Configuration

**Files to Check:**

1. **Socket.IO Client:**
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard-svelte/src/lib/socketio.js`
   - Verify subscribes to `mpm_event`
   - Check event filtering logic

2. **Event Display Logic:**
   - Dashboard components that render tool calls
   - Session grouping/filtering
   - Agent type classification

3. **Server-Side Routing:**
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/`
   - Event handlers and connection managers
   - Broadcasting logic

**Recommendation:** Trace event flow through:
```
Hook → Socket.IO Server → Broadcast → Dashboard Client → React/Svelte UI
```

Add console.log at each step to find where events disappear.

---

## Recommendations

### Immediate Actions

1. **Enable Debug Mode** and reproduce issue:
   ```bash
   export CLAUDE_MPM_HOOK_DEBUG=true
   /mpm-organize
   tail -f /tmp/hook-wrapper.log
   ```

2. **Check Session Correlation:**
   - Log PM session_id when Task delegation starts
   - Log sub-agent session_id when tool calls occur
   - Verify StateManager finds matching delegation

3. **Verify Dashboard Filtering:**
   - Check if dashboard groups by working directory
   - Ensure sub-agent session_id events are not filtered out
   - Test with dashboard filters disabled

### Code Improvements

1. **Session Hierarchy Tracking:**
   - Add `parent_session_id` field to sub-agent events
   - Store PM → sub-agent session mapping
   - Display parent/child relationship in dashboard

2. **Event Batching:**
   - For sub-agents making 50+ tool calls, batch events:
     - Emit summary event every 10 tool calls
     - Full events available in logs
     - Reduces dashboard noise

3. **Correlation Enhancement:**
   - Use working directory + timestamp window for fuzzy matching
   - Add agent type to event key for better grouping
   - Store correlation data in shared cache (not in-process)

### Documentation

1. **Update Developer Docs:**
   - Document sub-agent event flow with examples
   - Explain session ID correlation architecture
   - Troubleshooting guide for missing events

2. **Dashboard User Guide:**
   - How to filter by agent type
   - How to trace sub-agent tool calls
   - Understanding session hierarchy

---

## Conclusion

**The architecture SUPPORTS sub-agent event capture.** Hooks are configured for all Claude Code sessions including spawned agents.

**Most likely causes of missing events:**

1. **Dashboard filtering** - Events arrive but aren't displayed
2. **Session correlation** - Sub-agent session_id not matched to PM
3. **Event emission** - Socket.IO connection issues at high event rate
4. **Frontend grouping** - Sub-agent events not grouped under parent task

**Next Steps:**

1. Enable debug logging and reproduce issue
2. Verify events reach Socket.IO server
3. Check dashboard filtering/grouping logic
4. Test session correlation with logging

**NOT the issue:**
- Hook configuration (correctly set up for all sessions)
- Slash command filtering (doesn't affect sub-agent tool calls)
- Architecture design (single-path emission is correct)

---

## Files Analyzed

1. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_wrapper.sh` - Entry point
2. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py` - Main handler
3. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py` - Event routing
4. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/subagent_processor.py` - SubagentStop handling
5. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py` - Event emission
6. `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/installer.py` - Hook installation

---

## Appendix: Event Schema

**Normalized Event Structure:**

```json
{
  "event": "mpm_event",
  "type": "hook",
  "subtype": "pre_tool",
  "timestamp": "2025-12-23T10:30:00.000Z",
  "source": "mpm_hook",
  "session_id": "XYZ789...",
  "cwd": "/path/to/project",
  "correlation_id": "tool-call-uuid",
  "data": {
    "tool_name": "Read",
    "tool_parameters": {"file_path": "/path/to/file"},
    "working_directory": "/path/to/project",
    "git_branch": "main",
    "operation_type": "read",
    "is_file_operation": true
  }
}
```

**Sub-Agent Specific Fields:**

```json
{
  "event": "mpm_event",
  "type": "hook",
  "subtype": "subagent_stop",
  "data": {
    "agent_type": "project-organizer",
    "session_id": "XYZ789...",
    "reason": "completed",
    "is_successful_completion": true,
    "has_results": true,
    "structured_response": {
      "task_completed": true,
      "files_modified": ["file1", "file2"],
      "tools_used": ["Read", "Write", "Bash"]
    }
  }
}
```

---

**Research Completed:** 2025-12-23
**Confidence Level:** High (architecture analysis complete)
**Follow-Up Required:** Debug logging and dashboard investigation
