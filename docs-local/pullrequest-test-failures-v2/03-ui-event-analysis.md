# UI Event Handling & Socket.IO Analysis

**Date**: 2026-02-21
**Analyst**: UI Research Agent
**Task**: Analyze dashboard UI event handling and Socket.IO expectations

---

## Executive Summary

The dashboard UI has **two completely separate event handling systems**:

1. **General Event Stream** (socket store) - Handles 10 event types for the Events tab
2. **Config Event System** (+page.svelte direct listener) - Handles `config_event` for real-time config updates

The failing tests reference methods (`_emit_phase_event`, `_emit_event`) that **do not exist** in the implementation. The tests were written for a design specification that was never implemented.

---

## 1. What Events Does the UI Listen For?

### 1.1 Socket Store Event Types (`socket.svelte.ts:208`)

The main socket store registers listeners for **10 event types**:

| # | Event Name | Purpose |
|---|-----------|---------|
| 1 | `claude_event` | Default/catch-all for Claude activity |
| 2 | `hook_event` | Agent lifecycle (subagent_start, subagent_stop, todo_updated) |
| 3 | `tool_event` | Tool operations (pre_tool, post_tool, tool_use) |
| 4 | `cli_event` | CLI-related events |
| 5 | `system_event` | System heartbeat, ready, shutdown |
| 6 | `agent_event` | Agent delegation (agent.delegated, agent.returned) |
| 7 | `build_event` | Build-related events |
| 8 | `session_event` | Session lifecycle (session.started, session.ended) |
| 9 | `response_event` | API response lifecycle |
| 10 | `file_event` | File operations (file.read, file.write) |

**Additionally** (not in the array):
| Event | Handler | Purpose |
|-------|---------|---------|
| `event_history` | Replays buffered events on connect | Historical event delivery |
| `heartbeat` | Silent acknowledgment | Connection health |
| `reload` | `window.location.reload()` | Dev hot reload |
| `onAny` (catch-all) | Console logging | Debug/monitoring |

### 1.2 Config Event Listener (`+page.svelte:117`)

**Separate from the socket store**, the page component registers a direct listener:

```typescript
sock.on('config_event', (event: any) => {
    console.log('[Config] Received config_event:', event);
    handleConfigEvent(event);
});
```

This handles config-specific operations via `handleConfigEvent()` in `config.svelte.ts:890`.

### 1.3 Config Event Operations Handled (`config.svelte.ts:891-931`)

| Operation | Action |
|-----------|--------|
| `source_added` | Refresh sources list |
| `source_removed` | Refresh sources list |
| `source_updated` | Refresh sources list |
| `sync_progress` | Update sync status UI |
| `sync_completed` | Update sync status UI |
| `sync_failed` | Update sync status UI |
| `agent_deployed` | Refresh agent lists + summary |
| `agent_undeployed` | Refresh agent lists + summary |
| `skill_deployed` | Refresh skill lists + summary |
| `skill_undeployed` | Refresh skill lists + summary |
| `autoconfig_progress` | Notify autoconfig listeners (pipeline update) |
| `autoconfig_completed` | Resolve completion promise, fire success toast |
| `autoconfig_failed` | Reject completion promise |
| `external_change` | Show warning toast + refresh |

---

## 2. Expected Data Structures

### 2.1 General Event Payload (ClaudeEvent, `events.ts:1-16`)

```typescript
interface ClaudeEvent {
    id: string;
    event?: string;           // Socket event name
    type: string;             // Event type
    timestamp: string | number;
    data: unknown;
    agent?: string;
    sessionId?: string;       // camelCase (client)
    session_id?: string;      // snake_case (server)
    subtype?: string;
    source?: string;
    metadata?: unknown;
    cwd?: string;
    working_directory?: string;
    correlation_id?: string;
}
```

### 2.2 Config Event Payload (from backend `config_handler.py:9-17`)

```python
{
    "type": "config_event",
    "operation": str,        # "source_added", "autoconfig_progress", etc.
    "entity_type": str,      # "agent_source", "skill_source", "autoconfig"
    "entity_id": str | None, # Source ID or job_id
    "status": str,           # "started", "progress", "completed", "failed"
    "data": dict,            # Operation-specific payload
    "timestamp": str         # ISO 8601
}
```

### 2.3 AutoConfig Event Payload (`config.svelte.ts:743-746`)

```typescript
interface AutoConfigEvent {
    operation: 'autoconfig_progress' | 'autoconfig_completed' | 'autoconfig_failed';
    data: Record<string, any>;
}
```

### 2.4 AutoConfig Progress `data.phase` Values (used by UI pipeline)

The `AutoConfigPreview.svelte:44-51` component maps backend phases to pipeline stages:

```typescript
const phaseToStageMap: Record<string, number> = {
    'detecting': 0,
    'recommending': 1,
    'validating': 2,
    'deploying': 3,
    'deploying_skills': 4,
    'verifying': 5,
};
```

### 2.5 AutoConfig Completion Result (`config.svelte.ts:828-838`)

```typescript
{
    job_id: string;
    deployed_agents: string[];
    failed_agents: string[];
    deployed_skills: string[];
    skill_errors: string[];
    backup_id: string | null;
    duration_ms: number;
    needs_restart: boolean;
    verification: Record<string, any>;
}
```

---

## 3. Critical Mismatch: Tests vs UI vs Backend

### 3.1 Event Name Comparison Table

| Layer | Socket Event Name | How It's Emitted | Where It's Listened |
|-------|------------------|-----------------|-------------------|
| **Backend (config_handler.py)** | `config_event` | `sio.emit("config_event", event)` | +page.svelte line 117 |
| **Backend (core.py)** | `claude_event`, `hook_event`, etc. | `sio.emit(event_type, event_data)` | socket.svelte.ts line 211 |
| **Backend (autoconfig_handler.py)** | `config_event` | Via `ConfigEventHandler.emit_config_event()` | +page.svelte via handleConfigEvent |
| **UI Socket Store** | 10 event types | N/A (listener) | EventStream.svelte |
| **UI Config Handler** | `config_event` only | N/A (listener) | config.svelte.ts handleConfigEvent |

### 3.2 Key Finding: `config_event` is NOT in the Socket Store

**`config_event` is NOT in the socket store's `eventTypes` array.** It is handled by a completely separate listener in `+page.svelte`. This means:

- Config events do NOT appear in the EventStream view
- Config events are NOT stored in the events writable store
- Config events ONLY trigger store refreshes (fetch new data from API)
- This is by design - config events are "control signals", not "data events"

### 3.3 Test vs Implementation Comparison

| What Tests Expect | What Actually Exists | Match? |
|-------------------|---------------------|--------|
| `AutoConfigureCommand._emit_phase_event()` | **Does not exist** | **NO** |
| `RichProgressObserver._emit_event()` | **Does not exist** | **NO** |
| `get_socketio_server()` function | Not in auto_configure.py | **NO** |
| `get_event_emitter()` function | Exists in `monitor/event_emitter.py` but not used by CLI command | **PARTIAL** |
| Phase events: `toolchain_analysis`, `min_confidence_validation`, `skill_deployment`, `agent_archiving`, `configuration_completion`, `deployment_completed` | Backend uses: `autoconfig_progress`, `autoconfig_completed`, `autoconfig_failed` with `data.phase` subfield | **DIFFERENT** |
| Observer methods: `on_agent_deployment_started`, etc. | **EXISTS** on RichProgressObserver (lines 56-95) | **YES** |
| Observer `_emit_event` internal method | **Does not exist** - Observer only updates Rich console output | **NO** |

### 3.4 The Two Code Paths (Root Cause of Mismatches)

There are **two completely independent code paths** for auto-configure:

#### Path A: CLI (`claude-mpm auto-configure`)
```
User CLI → AutoConfigureCommand.run()
  → auto_config_manager.auto_configure()
    → RichProgressObserver.on_agent_deployment_started()  [console output only]
    → RichProgressObserver.on_agent_deployment_completed() [console output only]
    → RichProgressObserver.on_deployment_completed()       [console output only]
```
**No Socket.IO events emitted.** Observer only writes to Rich console.

#### Path B: Dashboard API (`/api/config/auto-configure/apply`)
```
Dashboard → HTTP POST /api/config/auto-configure/apply
  → autoconfig_handler.run_autoconfig_job()
    → ConfigEventHandler.emit_config_event("autoconfig_progress", ...)
    → ConfigEventHandler.emit_config_event("autoconfig_completed", ...)
  → Socket.IO "config_event" → UI +page.svelte → handleConfigEvent()
```
**Socket.IO events emitted.** UI receives real-time updates.

#### The Problem
The failing tests attempt to test **Path A** (CLI command) as if it emits Socket.IO events, but it never does. The Socket.IO event emission only happens in **Path B** (Dashboard API handler). The tests reference methods (`_emit_phase_event`, `_emit_event`) that were designed in the spec but **never implemented** on the CLI command or observer.

---

## 4. Is There a Mapping Layer?

### 4.1 Backend Event Categorization (`core.py:90-164`)

The `_categorize_event()` method maps subtype names to Socket.IO event categories:

```python
# Hook events
"subagent_start", "subagent_stop", "todo_updated" → "hook_event"

# Tool events
"pre_tool", "post_tool", "tool.start", "tool.end" → "tool_event"

# Session events
"session.started", "session.ended" → "session_event"

# Agent events
"agent.delegated", "agent.returned", "agent_start", "agent_end" → "agent_event"

# File events
"file.read", "file.write", "file.edit" → "file_event"

# Default for unknowns → "claude_event"
```

### 4.2 Config Events Bypass Categorization

Config events (`config_event`) are emitted directly by `ConfigEventHandler.emit_config_event()` with the event name `"config_event"`. They do NOT go through `_categorize_event()`. This is why they are handled separately by the UI.

---

## 5. What Events Does the Backend Currently Emit?

### 5.1 From SocketIOServerCore (HTTP API handler, `core.py:346-518`)

When receiving events via `POST /api/events`:
- Normalizes hook events to standard format
- Categorizes via `_categorize_event()` → emits as `claude_event`, `hook_event`, `tool_event`, etc.
- Adds to event buffer and history

### 5.2 From ConfigEventHandler (`config_handler.py:42-73`)

Direct `config_event` emissions for:
- Source CRUD operations
- Sync progress/completion
- External file changes

### 5.3 From autoconfig_handler.py (`autoconfig_handler.py:402-654`)

Via `ConfigEventHandler.emit_config_event()`:
- `autoconfig_progress` with phase/progress data
- `autoconfig_completed` with deployment results
- `autoconfig_failed` with error details

### 5.4 From agent_deployment_handler.py and skill_deployment_handler.py

Via `ConfigEventHandler.emit_config_event()`:
- `agent_deployed` / `agent_undeployed`
- `skill_deployed` / `skill_undeployed`

### 5.5 Heartbeat (`core.py:1092-1168`)

Periodic `system_event` with heartbeat data including uptime, client count, active sessions.

---

## 6. TODOs and Unimplemented Event Handling

### 6.1 Missing: CLI → Socket.IO Bridge

The RichProgressObserver **only** writes to the Rich console. There is no mechanism for the CLI command to emit Socket.IO events. The tests assume this bridge exists but it was never built.

### 6.2 Missing: `_emit_phase_event` on AutoConfigureCommand

This method is referenced in 4 test methods (`test_phase_0_*`, `test_phase_1_*`, `test_phase_2_*`, `test_phase_4_*`) but **does not exist** in the implementation. It was specified in the design docs but never implemented.

### 6.3 Missing: `_emit_event` on RichProgressObserver

This method is referenced in 5 test methods (`test_agent_deployment_started_*`, `test_agent_deployment_progress_*`, etc.) but **does not exist**. The observer methods exist but they only interact with Rich console, not Socket.IO.

### 6.4 `config_event` Not Visible in Event Stream

Config events are intentionally excluded from the general event stream. This is a design choice, not a bug - config events trigger store refreshes rather than appearing as timeline events.

---

## 7. Complete Event Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    DASHBOARD UI (+page.svelte)                   │
│                                                                  │
│  ┌──────────────────┐    ┌──────────────────────────────┐       │
│  │  Socket Store     │    │  Config Event Handler         │       │
│  │  socket.svelte.ts │    │  config.svelte.ts             │       │
│  │                   │    │                               │       │
│  │  Listens for:     │    │  Listens for:                 │       │
│  │  - claude_event   │    │  - config_event (only)        │       │
│  │  - hook_event     │    │                               │       │
│  │  - tool_event     │    │  Operations handled:          │       │
│  │  - cli_event      │    │  - source_added/removed       │       │
│  │  - system_event   │    │  - sync_progress/completed    │       │
│  │  - agent_event    │    │  - agent_deployed/undeployed  │       │
│  │  - build_event    │    │  - skill_deployed/undeployed  │       │
│  │  - session_event  │    │  - autoconfig_progress ◄──────┼─ Pipeline stages
│  │  - response_event │    │  - autoconfig_completed       │       │
│  │  - file_event     │    │  - autoconfig_failed          │       │
│  │                   │    │  - external_change            │       │
│  │  → EventStream    │    │  → Store refreshes / Toasts   │       │
│  └────────┬─────────┘    └──────────┬───────────────────┘       │
│           │                          │                           │
└───────────┼──────────────────────────┼───────────────────────────┘
            │                          │
     Socket.IO Connection      Socket.IO Connection
     (same socket, different event names)
            │                          │
┌───────────┴──────────────────────────┴───────────────────────────┐
│                    BACKEND SERVER (port 8765)                     │
│                                                                  │
│  ┌──────────────────────┐   ┌──────────────────────────┐        │
│  │ SocketIOServerCore    │   │ ConfigEventHandler        │        │
│  │                       │   │                           │        │
│  │ POST /api/events      │   │ emit_config_event()       │        │
│  │ → _categorize_event() │   │ → sio.emit("config_event")│        │
│  │ → sio.emit(category)  │   │                           │        │
│  │                       │   │ Used by:                   │        │
│  │ Emits: claude_event,  │   │ - config_sources routes    │        │
│  │ hook_event, tool_event│   │ - agent_deployment_handler │        │
│  │ etc.                  │   │ - skill_deployment_handler │        │
│  │                       │   │ - autoconfig_handler       │        │
│  └───────────────────────┘   │ - ConfigFileWatcher        │        │
│                              └──────────────────────────┘        │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Conclusion: Are the Tests Testing the Right Events?

### Verdict: The tests are testing **WRONG events** and **non-existent methods**.

| Issue | Severity | Detail |
|-------|----------|--------|
| Tests reference `_emit_phase_event` | **CRITICAL** | Method does not exist on AutoConfigureCommand |
| Tests reference `_emit_event` on observer | **CRITICAL** | Method does not exist on RichProgressObserver |
| Tests expect CLI to emit Socket.IO events | **CRITICAL** | CLI path has no Socket.IO integration |
| Phase names in tests differ from backend | **MAJOR** | Tests: `toolchain_analysis`, Backend: `detecting` |
| Tests patch non-existent imports | **MAJOR** | `get_socketio_server` not importable from cli module |
| Test integration test expects `events_emitted > 0` | **MAJOR** | No events are emitted in CLI flow |

### What the Tests SHOULD Be Testing

If the goal is to test the autoconfig event flow that the UI consumes, the tests should:

1. Test `autoconfig_handler.py` → `ConfigEventHandler.emit_config_event()` (the **actual** event emission path)
2. Test that `config_event` events with `operation="autoconfig_progress"` contain valid `data.phase` values matching the UI's `phaseToStageMap`
3. Test that `config_event` events with `operation="autoconfig_completed"` contain the fields the UI expects (`deployed_agents`, `failed_agents`, `deployed_skills`, `skill_errors`, `backup_id`, `duration_ms`, `needs_restart`, `verification`)
4. Test the Observer pattern separately (RichProgressObserver console output), without expecting Socket.IO integration
