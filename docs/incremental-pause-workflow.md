# Incremental Pause Workflow

## Overview

The **IncrementalPauseManager** captures actions incrementally after the auto-pause threshold (90% context usage) is crossed. This allows us to record the "wind-down" period as the user wraps up their work, providing a complete session history.

## Architecture

```
┌─────────────────────────┐
│ ContextUsageTracker     │
│ - Monitors token usage  │
│ - Detects 90% threshold │
└───────────┬─────────────┘
            │
            │ threshold_crossed
            ▼
┌─────────────────────────┐
│ IncrementalPauseManager │
│ - Creates JSONL file    │
│ - Appends actions       │
│ - Finalizes snapshot    │
└───────────┬─────────────┘
            │
            │ finalize()
            ▼
┌─────────────────────────┐
│ SessionPauseManager     │
│ - Creates JSON/YAML/MD  │
│ - Git commit (optional) │
│ - Updates LATEST pointer│
└─────────────────────────┘
```

## Data Flow

### 1. Threshold Detection

```python
from claude_mpm.services.infrastructure import ContextUsageTracker

tracker = ContextUsageTracker()
state = tracker.update_usage(input_tokens=50000, output_tokens=15000)

if tracker.should_auto_pause():
    # Context usage >= 90%, trigger incremental pause
    print(f"Auto-pause threshold reached: {state.percentage_used:.1f}%")
```

### 2. Start Incremental Pause

```python
from claude_mpm.services.cli import IncrementalPauseManager

manager = IncrementalPauseManager()

if not manager.is_pause_active():
    session_id = manager.start_incremental_pause(
        context_percentage=state.percentage_used / 100,
        initial_state=state.__dict__
    )
```

**What happens:**
- Creates `ACTIVE-PAUSE.jsonl` in `.claude-mpm/sessions/`
- Writes `pause_started` action with initial state
- Returns unique session ID (format: `session-YYYYMMDD-HHMMSS`)

**JSONL Format:**
```jsonl
{"type": "pause_started", "timestamp": "2026-01-06T12:00:00Z", "session_id": "session-20260106-120000", "data": {"context_percentage": 0.90, "initial_state": {...}}, "context_percentage": 0.90}
```

### 3. Record Actions During Wind-Down

```python
# Record tool calls
manager.append_action(
    action_type="tool_call",
    action_data={"tool": "Read", "path": "/src/main.py", "lines": 150},
    context_percentage=0.91
)

# Record assistant responses
manager.append_action(
    action_type="assistant_response",
    action_data={"summary": "Analyzed code structure and identified issues"},
    context_percentage=0.92
)

# Record user messages
manager.append_action(
    action_type="user_message",
    action_data={"message": "Can you summarize what we've done?"},
    context_percentage=0.93
)

# Record system events
manager.append_action(
    action_type="system_event",
    action_data={"event": "memory_warning", "available_mb": 500},
    context_percentage=0.93
)
```

**Action Types:**
- `tool_call`: Claude Code tool invocation (Read, Write, Bash, etc.)
- `assistant_response`: Claude's text response to user
- `user_message`: User input message
- `system_event`: System-level events (warnings, errors, etc.)
- `pause_started`: Initial pause trigger (auto-created)
- `pause_finalized`: Final action before snapshot (auto-created)

**What happens:**
- Each action is appended atomically to `ACTIVE-PAUSE.jsonl`
- File is flushed to disk immediately (crash-safe)
- Each line is a self-contained JSON object

### 4. Get Pause Summary (Optional)

```python
summary = manager.get_pause_summary()

print(f"Session: {summary['session_id']}")
print(f"Actions: {summary['action_count']}")
print(f"Context: {summary['context_range'][0]:.1%} -> {summary['context_range'][1]:.1%}")
print(f"Duration: {summary['duration_seconds']}s")
```

**Summary Fields:**
- `session_id`: Unique session identifier
- `action_count`: Total actions recorded (including `pause_started`)
- `duration_seconds`: Time since pause started
- `context_range`: Tuple of (start_percentage, current_percentage)
- `pause_started_at`: ISO timestamp when pause started
- `last_action_type`: Type of most recent action
- `last_updated`: ISO timestamp of last action

### 5. Finalize Pause

#### Option A: Full Snapshot (Recommended)

```python
final_path = manager.finalize_pause(create_full_snapshot=True)
```

**What happens:**
1. Appends `pause_finalized` action with statistics
2. Reads all actions from `ACTIVE-PAUSE.jsonl`
3. Delegates to `SessionPauseManager` to create:
   - `session-YYYYMMDD-HHMMSS.json` (machine-readable)
   - `session-YYYYMMDD-HHMMSS.yaml` (human-readable)
   - `session-YYYYMMDD-HHMMSS.md` (documentation)
4. Updates `LATEST-SESSION.txt` pointer
5. Renames `ACTIVE-PAUSE.jsonl` to `session-YYYYMMDD-HHMMSS-incremental.jsonl`
6. Returns path to JSON file

**Enriched State:**

The JSON/YAML/MD files include an `incremental_pause` section:

```json
{
  "session_id": "session-20260106-120000",
  "paused_at": "2026-01-06T12:05:00Z",
  "duration_hours": 0.08,
  "context_usage": {
    "tokens_used": 186000,
    "tokens_total": 200000,
    "percentage": 93.0
  },
  "incremental_pause": {
    "enabled": true,
    "action_count": 15,
    "duration_seconds": 300,
    "context_range": [0.90, 0.93],
    "tool_calls": 8,
    "actions_summary": [
      {"type": "tool_call", "timestamp": "2026-01-06T12:04:00Z"},
      {"type": "assistant_response", "timestamp": "2026-01-06T12:04:30Z"}
    ]
  }
}
```

#### Option B: Minimal Finalization (Archive Only)

```python
archive_path = manager.finalize_pause(create_full_snapshot=False)
```

**What happens:**
1. Appends `pause_finalized` action
2. Renames `ACTIVE-PAUSE.jsonl` to `session-YYYYMMDD-HHMMSS-incremental.jsonl`
3. Returns path to JSONL archive
4. **No** JSON/YAML/MD files created

**Use when:**
- Quick finalization needed
- Full snapshot not required
- Debugging or testing

### 6. Discard Pause (Alternative)

```python
discarded = manager.discard_pause()
```

**What happens:**
- Deletes `ACTIVE-PAUSE.jsonl` without archiving
- Returns `True` if pause was active, `False` otherwise
- No session files created

**Use when:**
- User decides to continue working
- False positive auto-pause trigger
- Testing or debugging

## File Structure

After finalization, the sessions directory contains:

```
.claude-mpm/sessions/
├── LATEST-SESSION.txt                        # Pointer to most recent session
├── session-20260106-120000.json              # Machine-readable state
├── session-20260106-120000.yaml              # Human-readable state
├── session-20260106-120000.md                # Documentation
└── session-20260106-120000-incremental.jsonl # Action log
```

### JSONL Archive Format

Each line is a complete JSON object:

```jsonl
{"type": "pause_started", "timestamp": "2026-01-06T12:00:00Z", "session_id": "session-20260106-120000", "data": {...}, "context_percentage": 0.90}
{"type": "tool_call", "timestamp": "2026-01-06T12:01:00Z", "session_id": "session-20260106-120000", "data": {...}, "context_percentage": 0.91}
{"type": "assistant_response", "timestamp": "2026-01-06T12:02:00Z", "session_id": "session-20260106-120000", "data": {...}, "context_percentage": 0.92}
{"type": "pause_finalized", "timestamp": "2026-01-06T12:05:00Z", "session_id": "session-20260106-120000", "data": {...}, "context_percentage": 0.93}
```

**Benefits:**
- **Crash-safe**: Each action is flushed immediately
- **Append-only**: Efficient incremental writes
- **Self-contained**: Each line is valid JSON
- **Debuggable**: Easy to inspect with `cat` or `jq`

## Integration with Hooks

### Hook Event Handlers

The `IncrementalPauseManager` will be integrated with Claude Code hooks to automatically capture actions:

```python
# In hook event handlers (future implementation)

def on_tool_call_completed(tool_name: str, tool_args: dict, result: Any):
    """Hook called after tool execution completes."""
    if pause_manager.is_pause_active():
        pause_manager.append_action(
            action_type="tool_call",
            action_data={
                "tool": tool_name,
                "args": tool_args,
                "result_summary": summarize_result(result)
            },
            context_percentage=tracker.get_current_state().percentage_used / 100
        )

def on_assistant_response(response_text: str):
    """Hook called after assistant generates response."""
    if pause_manager.is_pause_active():
        pause_manager.append_action(
            action_type="assistant_response",
            action_data={
                "summary": response_text[:200],  # First 200 chars
                "length": len(response_text)
            },
            context_percentage=tracker.get_current_state().percentage_used / 100
        )

def on_conversation_end():
    """Hook called when conversation ends."""
    if pause_manager.is_pause_active():
        pause_manager.finalize_pause(create_full_snapshot=True)
```

## Error Handling

### Concurrent Access

**Problem:** Multiple processes trying to write to `ACTIVE-PAUSE.jsonl` simultaneously.

**Solution:** File locking is handled by Python's file operations:
- `open("a")` mode is atomic for single-line appends
- Each action is a single line
- No need for explicit locking

### Corrupted JSONL File

**Problem:** Crash during write leaves incomplete JSON line.

**Solution:**
- Read actions using `PauseAction.from_json_line(line.strip())`
- Ignore empty lines
- Skip invalid JSON lines (log warning)

```python
actions = []
with open(jsonl_path) as f:
    for line in f:
        if not line.strip():
            continue
        try:
            actions.append(PauseAction.from_json_line(line))
        except json.JSONDecodeError as e:
            logger.warning(f"Skipping invalid JSON line: {e}")
```

### Orphaned ACTIVE-PAUSE.jsonl

**Problem:** `ACTIVE-PAUSE.jsonl` exists on startup (previous crash).

**Solution:**
- Check `is_pause_active()` on startup
- Prompt user to resume or discard
- Auto-finalize with timestamp recovery

```python
def recover_orphaned_pause():
    """Recover from orphaned ACTIVE-PAUSE.jsonl."""
    if manager.is_pause_active():
        summary = manager.get_pause_summary()
        print(f"Found incomplete pause session: {summary['session_id']}")
        print(f"  - {summary['action_count']} actions recorded")
        print(f"  - Started: {summary['pause_started_at']}")

        choice = input("Finalize (f), discard (d), or continue (c)? ")

        if choice == "f":
            manager.finalize_pause()
        elif choice == "d":
            manager.discard_pause()
        # else: continue appending to existing session
```

## Performance Considerations

### Memory Usage

- **JSONL appending**: O(1) memory per action (streaming write)
- **Reading actions**: O(n) memory where n = number of actions
- **Finalization**: Entire action list loaded into memory (typically <100 actions)

**Optimization:** Limit `actions_summary` in enriched state to last 10 actions.

### Disk I/O

- **Append operation**: Single write + flush per action (~1ms)
- **Finalization**: Single read of entire JSONL file
- **No intermediate files**: Actions written directly to final location

**Best Practice:** Call `finalize_pause()` only once when session ends.

### File Size

- **Typical action**: ~200-500 bytes JSON
- **100 actions**: ~20-50 KB JSONL file
- **Full snapshot**: ~10-20 KB JSON/YAML/MD files

**Total disk usage per session:** ~30-70 KB

## Testing

See `examples/incremental_pause_usage.py` for comprehensive examples:

```bash
# Run basic workflow
python3 examples/incremental_pause_usage.py

# Test discard workflow
python3 examples/incremental_pause_usage.py discard

# Test resume workflow
python3 examples/incremental_pause_usage.py resume
```

## API Reference

### IncrementalPauseManager

```python
class IncrementalPauseManager:
    """Manages incremental capture of actions during auto-pause wind-down."""

    def __init__(self, project_path: Optional[Path] = None):
        """Initialize with project path for sessions directory."""

    def is_pause_active(self) -> bool:
        """Check if there's an active incremental pause in progress."""

    def start_incremental_pause(
        self, context_percentage: float, initial_state: dict
    ) -> str:
        """Start a new incremental pause session."""

    def append_action(
        self, action_type: str, action_data: dict, context_percentage: float
    ) -> None:
        """Append an action to the active pause file."""

    def get_recorded_actions(self) -> List[PauseAction]:
        """Read all actions from the current pause session."""

    def finalize_pause(self, create_full_snapshot: bool = True) -> Optional[Path]:
        """Finalize the incremental pause into a complete session snapshot."""

    def discard_pause(self) -> bool:
        """Discard the current incremental pause without finalizing."""

    def get_pause_summary(self) -> Optional[dict]:
        """Get summary of current pause session."""
```

### PauseAction

```python
@dataclass
class PauseAction:
    """Single action recorded during incremental pause."""

    type: str                    # Action type
    timestamp: str               # ISO format timestamp
    session_id: str              # Unique session identifier
    data: dict                   # Action-specific data
    context_percentage: float    # Context usage when recorded

    def to_json_line(self) -> str:
        """Convert to JSON line for JSONL format."""

    @classmethod
    def from_json_line(cls, line: str) -> "PauseAction":
        """Parse from JSON line."""
```

## Next Steps

1. **Integrate with AutoPauseHandler** - Automatic action capture via hooks
2. **Add resume workflow** - Load previous session and continue
3. **Implement analytics** - Track action patterns and context usage
4. **Add compression** - Compress archived JSONL files for long-term storage

## See Also

- [Session Pause Manager](../src/claude_mpm/services/cli/session_pause_manager.py) - Full snapshot creation
- [Context Usage Tracker](../src/claude_mpm/services/infrastructure/context_usage_tracker.py) - Token usage monitoring
- [Auto-Pause Workflow](./auto-pause-workflow.md) - Complete auto-pause system design (coming soon)
