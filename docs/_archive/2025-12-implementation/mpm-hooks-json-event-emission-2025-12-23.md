# MPM Hooks System and Claude Code Event Format Research

**Date:** 2025-12-23
**Researcher:** Claude (Research Agent)
**Purpose:** Understand MPM hooks implementation and Claude Code event format for adding JSON event emission

---

## Executive Summary

The MPM (Multi-Agent Project Manager) system has a comprehensive hooks implementation that integrates with Claude Code's event system. Events are normalized and emitted via Socket.IO to a dashboard for real-time monitoring. This research documents the current architecture and provides recommendations for adding JSON event emission to the hooks system.

---

## 1. MPM Hooks Implementation

### Location
- **Primary Hook Handler:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py`
- **Hook Manager:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/core/hook_manager.py`
- **Event Handlers:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py`

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Hook Execution Flow                      │
└─────────────────────────────────────────────────────────────┘

Claude Code Hook Trigger
          ↓
hook_handler.py (ClaudeHookHandler)
          ↓
_route_event() → EventHandlers
          ↓
event_handlers.py (handle_user_prompt_fast, handle_pre_tool_fast, etc.)
          ↓
ConnectionManagerService._emit_socketio_event()
          ↓
EventNormalizer.normalize()
          ↓
Socket.IO Server → Dashboard
```

### Key Components

#### 1. **ClaudeHookHandler** (`hook_handler.py`)
- **Purpose:** Main entry point for Claude Code hooks
- **Initialization:** Singleton pattern with thread-safe access
- **Event Processing:** Reads JSON from stdin, routes to appropriate handlers
- **Timeout Protection:** 10-second timeout with SIGALRM to prevent hangs
- **Continue Protocol:** Always outputs `{"action": "continue"}` to Claude Code

**Hook Types Supported:**
- `UserPromptSubmit` - User prompt events
- `PreToolUse` - Before tool execution
- `PostToolUse` - After tool execution
- `Notification` - System notifications
- `Stop` - Session stop events
- `SubagentStop` - Subagent completion
- `SubagentStart` / `SessionStart` - Session start
- `AssistantResponse` - Assistant responses

#### 2. **HookManager** (`core/hook_manager.py`)
- **Purpose:** Manual hook triggering from PM operations (TodoWrite, etc.)
- **Why Needed:** PM runs directly in Python, bypassing Claude Code's hook system
- **Background Processing:** Async hook queue with dedicated thread
- **Error Memory:** Tracks failing hooks to prevent repeated errors
- **Session Tracking:** Maintains session ID for event correlation

**Hook Event Structure:**
```python
{
    "hook_event_name": "PreToolUse",  # Hook type
    "session_id": "uuid-string",      # Session identifier
    "timestamp": "2025-12-23T10:30:00Z",
    "tool_name": "TodoWrite",         # Tool-specific fields
    "tool_args": {...}
}
```

#### 3. **EventHandlers** (`hooks/claude_hooks/event_handlers.py`)
- **Purpose:** Individual handlers for each hook type
- **Data Enrichment:** Adds git branch, working dir, metadata
- **Tool Analysis:** Classifies operations, assesses security risk
- **Correlation:** Generates `tool_call_id` for pre/post correlation

**Pre-Tool Event Data:**
```python
{
    "tool_name": "Write",
    "operation_type": "file_write",
    "tool_parameters": {"file_path": "..."},
    "session_id": "uuid",
    "working_directory": "/path/to/project",
    "git_branch": "main",
    "timestamp": "2025-12-23T10:30:00Z",
    "parameter_count": 2,
    "is_file_operation": True,
    "is_execution": False,
    "is_delegation": False,
    "security_risk": "low",
    "correlation_id": "tool-call-uuid"
}
```

---

## 2. Claude Code Event Format

### Event Normalization System

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/services/socketio/event_normalizer.py`

### Normalized Event Schema

All events are normalized to this consistent structure before emission:

```python
{
    "event": "claude_event",           # Socket.IO event name (always constant)
    "source": "hook",                  # Event source (hook, dashboard, system, etc.)
    "type": "hook",                    # Main category (hook, system, session, file, etc.)
    "subtype": "pre_tool",             # Specific event type
    "timestamp": "2025-12-23T10:30:00Z",
    "data": {                          # Event payload
        "tool_name": "Write",
        "tool_parameters": {...},
        # ... other event-specific data
    },
    "correlation_id": "uuid"           # Optional: for correlating related events
}
```

### Event Categories

```python
class EventType(Enum):
    HOOK = "hook"              # Claude Code hook events
    SYSTEM = "system"          # System health and status
    SESSION = "session"        # Session lifecycle
    FILE = "file"              # File system events
    CONNECTION = "connection"  # Client connections
    MEMORY = "memory"          # Memory system
    GIT = "git"                # Git operations
    TODO = "todo"              # Todo list updates
    TICKET = "ticket"          # Ticket system
    AGENT = "agent"            # Agent delegation
    ERROR = "error"            # Error events
    PERFORMANCE = "performance" # Performance metrics
    CLAUDE = "claude"          # Claude process
    TEST = "test"              # Test events
    CODE = "code"              # Code analysis
    TOOL = "tool"              # Tool events
    SUBAGENT = "subagent"      # Subagent events
```

### Event Sources

```python
class EventSource(Enum):
    HOOK = "hook"         # Claude Code hooks
    DASHBOARD = "dashboard" # Dashboard UI
    SYSTEM = "system"     # System/server
    AGENT = "agent"       # Agent operations
    CLI = "cli"           # CLI commands
    API = "api"           # API calls
    TEST = "test"         # Test scripts
```

---

## 3. Event Emission Architecture

### Single-Path Emission Architecture

**Critical Design:** The system uses a SINGLE-PATH emission to eliminate duplicates.

```
Hook Event
    ↓
ConnectionManagerService.emit_event()
    ↓
EventNormalizer.normalize()
    ↓
Primary Path: SocketIO Connection Pool (direct async)
    ↓ (if fails)
Fallback Path: HTTP POST to Monitor Server
    ↓
Socket.IO Server (daemon)
    ↓
Dashboard (WebSocket clients)
```

### ConnectionManagerService

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/services/connection_manager.py`

```python
def emit_event(self, namespace: str, event: str, data: dict):
    """Emit event through direct Socket.IO with HTTP fallback.

    🚨 CRITICAL: Single-path emission only - no EventBus
    """
    # Create normalized event
    raw_event = {
        "type": "hook",
        "subtype": event,  # e.g., "pre_tool", "user_prompt"
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "source": "claude_hooks",
        "correlation_id": data.get("tool_call_id")
    }

    # Normalize
    normalized_event = self.event_normalizer.normalize(raw_event, source="hook")

    # Emit via connection pool (primary)
    if self.connection_pool:
        self.connection_pool.emit("claude_event", normalized_event.to_dict())
    else:
        # HTTP fallback
        self._try_http_fallback(normalized_event.to_dict())
```

### Socket.IO Server

**Location:** `/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/socketio_daemon.py`

- **Daemon Process:** Runs persistently in background
- **Port:** Default 8765 (configurable)
- **PID File:** `~/.claude-mpm/socketio-server.pid`
- **Port Discovery:** Stores actual port in `~/.claude-mpm/socketio-port`

---

## 4. Integration Points for JSON Event Emission

### Where Hooks Are Triggered

1. **Claude Code Hook Events** (automatic)
   - User prompt submission
   - Pre-tool use
   - Post-tool use
   - Session start/stop
   - Subagent events

2. **Manual Hook Triggering** (via HookManager)
   - PM operations (TodoWrite, etc.)
   - Direct API calls
   - Test scenarios

### Current Event Flow

```
1. Event occurs (user prompt, tool use, etc.)
2. hook_handler.py receives event from Claude Code
3. Event routed to specific handler (e.g., handle_pre_tool_fast)
4. Handler enriches event with metadata
5. ConnectionManagerService.emit_event() called
6. EventNormalizer transforms to standard schema
7. Emitted via Socket.IO → Dashboard
```

---

## 5. Recommended Event Schema for MPM Hooks

### Base Hook Event Format

```json
{
  "event": "claude_event",
  "source": "hook",
  "type": "hook",
  "subtype": "pre_tool",
  "timestamp": "2025-12-23T10:30:00.123Z",
  "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
  "data": {
    "session_id": "abc123",
    "working_directory": "/Users/masa/Projects/claude-mpm",
    "git_branch": "main",
    "tool_name": "Write",
    "operation_type": "file_write",
    "tool_parameters": {
      "file_path": "/path/to/file.py",
      "content_preview": "# Python code..."
    },
    "security_risk": "low",
    "is_file_operation": true,
    "is_execution": false,
    "is_delegation": false
  }
}
```

### User Prompt Event

```json
{
  "event": "claude_event",
  "source": "hook",
  "type": "hook",
  "subtype": "user_prompt",
  "timestamp": "2025-12-23T10:30:00.123Z",
  "data": {
    "session_id": "abc123",
    "prompt_text": "Write a function to parse JSON",
    "prompt_preview": "Write a function to parse JSON",
    "prompt_length": 31,
    "working_directory": "/Users/masa/Projects/claude-mpm",
    "git_branch": "main",
    "is_command": false,
    "contains_code": false,
    "urgency": "normal"
  }
}
```

### Subagent Stop Event

```json
{
  "event": "claude_event",
  "source": "hook",
  "type": "hook",
  "subtype": "subagent_stop",
  "timestamp": "2025-12-23T10:30:00.123Z",
  "data": {
    "session_id": "abc123",
    "agent_type": "research",
    "exit_code": 0,
    "duration_seconds": 45.2,
    "output_length": 1234,
    "success": true,
    "working_directory": "/Users/masa/Projects/claude-mpm",
    "git_branch": "main"
  }
}
```

---

## 6. Implementation Recommendations

### Option 1: Extend Existing Event Emission (Recommended)

**Leverage the existing ConnectionManagerService:**

```python
# In hook_handler.py or event_handlers.py
def emit_json_event(self, hook_type: str, event_data: dict):
    """Emit a JSON event for MPM hooks."""
    # Event is automatically normalized by ConnectionManagerService
    self.hook_handler._emit_socketio_event("", hook_type, event_data)
```

**Pros:**
- Uses proven event normalization system
- Automatic Socket.IO emission with HTTP fallback
- Consistent with existing architecture
- Dashboard integration automatic

**Cons:**
- Tied to Socket.IO server availability
- Requires daemon process running

### Option 2: Direct JSON Output (Simple)

**Add JSON logging alongside Socket.IO emission:**

```python
import json
import sys

def emit_json_to_stdout(event_data: dict):
    """Emit JSON event to stdout for external consumption."""
    json_event = {
        "event": "claude_event",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **event_data
    }
    print(f"CLAUDE_EVENT:{json.dumps(json_event)}", file=sys.stderr)
```

**Pros:**
- Simple implementation
- No external dependencies
- Works without Socket.IO server

**Cons:**
- Separate from main event system
- No automatic normalization
- Manual parsing required

### Option 3: Event Bus Integration

**Create an event bus for multiple consumers:**

```python
class HookEventBus:
    def __init__(self):
        self.subscribers = []

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def emit(self, event_data):
        normalized = EventNormalizer().normalize(event_data, source="hook")
        for subscriber in self.subscribers:
            subscriber(normalized.to_dict())
```

**Pros:**
- Multiple consumers possible
- Decoupled architecture
- Flexible routing

**Cons:**
- More complex
- Potential for duplicate events (see architecture note)
- Requires careful management

---

## 7. Key Files for Implementation

### Files to Modify

1. **`hook_handler.py`** - Add JSON emission in `_route_event()`
2. **`event_handlers.py`** - Add JSON emission in individual handlers
3. **`connection_manager.py`** - Optionally extend emit logic

### Files to Reference

1. **`event_normalizer.py`** - Event schema and normalization
2. **`hook_manager.py`** - Manual hook triggering patterns
3. **`socketio_daemon.py`** - Socket.IO server integration

### Configuration Files

1. **`~/.claude/hooks/claude_hooks.json`** - Hook configuration
2. **`~/.claude-mpm/socketio-port`** - Socket.IO server port

---

## 8. Testing Strategy

### Unit Tests
- Test event normalization with various formats
- Test JSON serialization of hook events
- Test correlation_id generation and tracking

### Integration Tests
- Trigger hooks and verify JSON output
- Test Socket.IO emission and dashboard reception
- Test HTTP fallback when Socket.IO unavailable

### End-to-End Tests
- Run Claude Code with hooks enabled
- Verify events appear in dashboard
- Verify JSON format consistency

---

## 9. Gotchas and Considerations

### 1. **Duplicate Event Prevention**
- System uses SINGLE-PATH emission architecture
- DO NOT add EventBus or additional emission points
- See `docs/developer/EVENT_EMISSION_ARCHITECTURE.md`

### 2. **Hook Timeout Protection**
- All hooks have 10-second timeout (SIGALRM)
- Must call `_continue_execution()` before timeout
- Emission should be non-blocking

### 3. **Correlation IDs**
- Generated for PreToolUse events
- Stored via CorrelationManager for cross-process retrieval
- Used to link pre_tool → post_tool events

### 4. **Session Tracking**
- Session ID from `CLAUDE_MPM_SESSION_ID` environment variable
- Used for grouping events from same session
- Important for delegation tracking

### 5. **Error Memory**
- HookManager tracks failing hooks
- Skips hooks that repeatedly fail
- Reset via `rm ~/.claude-mpm/hook_errors.json`

### 6. **Socket.IO Availability**
- Hooks work without Socket.IO server (HTTP fallback)
- Check server status: `claude-mpm-socketio status`
- Start server: `claude-mpm-socketio start`

---

## 10. Next Steps

### Immediate Actions

1. **Review Event Schema** - Confirm JSON format meets requirements
2. **Choose Implementation** - Select Option 1 (recommended) or Option 2
3. **Add JSON Emission** - Implement in event handlers
4. **Test Thoroughly** - Unit, integration, and E2E tests
5. **Document** - Update developer docs with JSON event format

### Future Enhancements

1. **Event Filtering** - Allow filtering by type/subtype
2. **Event Storage** - Persist events to database
3. **Event Replay** - Replay events for debugging
4. **Performance Monitoring** - Track emission latency
5. **Schema Versioning** - Version event schema for evolution

---

## 11. References

### Documentation
- Event Emission Architecture: `docs/developer/EVENT_EMISSION_ARCHITECTURE.md`
- Hook System: `docs/hooks/` (if exists)
- Socket.IO Integration: `docs/socketio/` (if exists)

### Code Examples
- Hook Handler Tests: `tests/hooks/claude_hooks/test_hook_handler_*.py`
- Event Handler Tests: (look for event handler tests)
- Integration Tests: `tests/test_hook_isolation.py`

### Configuration
- Hook Config: `~/.claude/hooks/claude_hooks.json`
- MPM Config: `~/.claude-mpm/`
- Socket.IO PID: `~/.claude-mpm/socketio-server.pid`

---

## Appendix A: Complete Event Type Mapping

```python
# From EventNormalizer.EVENT_MAPPINGS
{
    # Hook events
    "pre_tool": (EventType.HOOK, "pre_tool"),
    "post_tool": (EventType.HOOK, "post_tool"),
    "pre_response": (EventType.HOOK, "pre_response"),
    "post_response": (EventType.HOOK, "post_response"),
    "hook_event": (EventType.HOOK, "generic"),

    # Legacy formats
    "UserPrompt": (EventType.HOOK, "user_prompt"),
    "TestStart": (EventType.TEST, "start"),
    "TestEnd": (EventType.TEST, "end"),
    "ToolCall": (EventType.TOOL, "call"),
    "SubagentStart": (EventType.SUBAGENT, "start"),
    "SubagentStop": (EventType.SUBAGENT, "stop"),

    # System events
    "heartbeat": (EventType.SYSTEM, "heartbeat"),
    "system_status": (EventType.SYSTEM, "status"),

    # Session events
    "session_started": (EventType.SESSION, "started"),
    "session_ended": (EventType.SESSION, "ended"),

    # File events
    "file_changed": (EventType.FILE, "changed"),
    "file_created": (EventType.FILE, "created"),
    "file_deleted": (EventType.FILE, "deleted"),

    # Connection events
    "client_connected": (EventType.CONNECTION, "connected"),
    "client_disconnected": (EventType.CONNECTION, "disconnected"),

    # Memory events
    "memory_loaded": (EventType.MEMORY, "loaded"),
    "memory_created": (EventType.MEMORY, "created"),
    "memory_updated": (EventType.MEMORY, "updated"),
    "memory_injected": (EventType.MEMORY, "injected"),

    # Git events
    "git_operation": (EventType.GIT, "operation"),
    "git_commit": (EventType.GIT, "commit"),

    # Todo events
    "todo_updated": (EventType.TODO, "updated"),
    "todo_created": (EventType.TODO, "created"),

    # Ticket events
    "ticket_created": (EventType.TICKET, "created"),
    "ticket_updated": (EventType.TICKET, "updated"),

    # Agent events
    "agent_delegated": (EventType.AGENT, "delegated"),
    "agent_completed": (EventType.AGENT, "completed"),

    # Claude events
    "claude_status": (EventType.CLAUDE, "status"),
    "claude_output": (EventType.CLAUDE, "output"),

    # Error events
    "error": (EventType.ERROR, "general"),
    "error_occurred": (EventType.ERROR, "occurred"),

    # Performance events
    "performance": (EventType.PERFORMANCE, "metric"),
    "performance_metric": (EventType.PERFORMANCE, "metric"),
}
```

---

## Appendix B: Example Integration Code

### Adding JSON Emission to Pre-Tool Hook

```python
# In event_handlers.py

def handle_pre_tool_fast(self, event):
    """Handle pre-tool use with comprehensive data capture and JSON emission."""

    # ... existing event processing code ...

    pre_tool_data = {
        "tool_name": tool_name,
        "operation_type": operation_type,
        "tool_parameters": tool_params,
        "session_id": event.get("session_id", ""),
        "working_directory": working_dir,
        "git_branch": git_branch,
        "timestamp": timestamp,
        "correlation_id": tool_call_id,
        # ... other fields ...
    }

    # Existing Socket.IO emission
    self.hook_handler._emit_socketio_event("", "pre_tool", pre_tool_data)

    # NEW: Optional JSON emission for external consumers
    if os.environ.get("MPM_EMIT_JSON_EVENTS", "false").lower() == "true":
        self._emit_json_event("pre_tool", pre_tool_data)

def _emit_json_event(self, event_type: str, data: dict):
    """Emit JSON event to stderr for external consumption."""
    json_event = {
        "event": "claude_event",
        "source": "hook",
        "type": "hook",
        "subtype": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data
    }
    # Use stderr to avoid interfering with stdout (which Claude Code monitors)
    print(f"MPM_HOOK_EVENT:{json.dumps(json_event)}", file=sys.stderr)
```

---

**End of Research Document**
