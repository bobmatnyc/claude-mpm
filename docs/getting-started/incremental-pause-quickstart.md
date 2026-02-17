# IncrementalPauseManager Quick Start

## 5-Minute Integration Guide

### Import

```python
from claude_mpm.services.cli import IncrementalPauseManager
from claude_mpm.services.infrastructure import ContextUsageTracker
```

### Basic Workflow

```python
# 1. Initialize services
tracker = ContextUsageTracker()
manager = IncrementalPauseManager()

# 2. Monitor context usage
state = tracker.update_usage(input_tokens=50000, output_tokens=15000)

# 3. Trigger auto-pause at 90%
if tracker.should_auto_pause() and not manager.is_pause_active():
    session_id = manager.start_incremental_pause(
        context_percentage=state.percentage_used / 100,
        initial_state=state.__dict__
    )

# 4. Record actions during wind-down
if manager.is_pause_active():
    manager.append_action(
        action_type="tool_call",
        action_data={"tool": "Read", "path": "/src/main.py"},
        context_percentage=0.91
    )

# 5. Finalize when session ends
final_path = manager.finalize_pause(create_full_snapshot=True)
# OR: Discard if user continues working
manager.discard_pause()
```

## Action Types

| Type | Purpose | Example Data |
|------|---------|--------------|
| `tool_call` | Claude Code tool invocation | `{"tool": "Read", "path": "/file.py"}` |
| `assistant_response` | Claude's text response | `{"summary": "Analyzed code..."}` |
| `user_message` | User input | `{"message": "Can you help?"}` |
| `system_event` | System-level events | `{"event": "memory_warning"}` |

## Files Created

After `finalize_pause(create_full_snapshot=True)`:

```
.claude-mpm/sessions/
├── session-YYYYMMDD-HHMMSS.json              # Machine-readable
├── session-YYYYMMDD-HHMMSS.yaml              # Human-readable
├── session-YYYYMMDD-HHMMSS.md                # Documentation
└── session-YYYYMMDD-HHMMSS-incremental.jsonl # Action log
```

## Common Patterns

### Check for Active Pause

```python
if manager.is_pause_active():
    print("Wind-down period is active")
```

### Get Pause Summary

```python
summary = manager.get_pause_summary()
print(f"Actions: {summary['action_count']}")
print(f"Duration: {summary['duration_seconds']}s")
print(f"Context: {summary['context_range'][0]:.1%} → {summary['context_range'][1]:.1%}")
```

### Resume from Previous Session

```python
from pathlib import Path

sessions_dir = Path.cwd() / ".claude-mpm" / "sessions"
latest_file = sessions_dir / "LATEST-SESSION.txt"

if latest_file.exists():
    content = latest_file.read_text()
    # Extract session ID and read markdown
    session_id = content.split("Latest Session:")[1].split("\n")[0].strip()
    md_file = sessions_dir / f"{session_id}.md"
    print(md_file.read_text())
```

## Error Handling

```python
try:
    session_id = manager.start_incremental_pause(0.90, initial_state)
except RuntimeError as e:
    # Pause already active or other error
    print(f"Failed to start pause: {e}")

try:
    manager.append_action("tool_call", {"tool": "Read"}, 0.91)
except RuntimeError as e:
    # No active pause or append failed
    print(f"Failed to append action: {e}")
```

## Testing

```bash
# Run example workflows
python3 examples/incremental_pause_usage.py          # Full workflow
python3 examples/incremental_pause_usage.py discard  # Discard example
python3 examples/incremental_pause_usage.py resume   # Resume example
```

## Next Steps

1. Read full documentation: [`docs/incremental-pause-workflow.md`](./incremental-pause-workflow.md)
2. Review implementation: [`src/claude_mpm/services/cli/incremental_pause_manager.py`](../src/claude_mpm/services/cli/incremental_pause_manager.py)
3. Study examples: [`examples/incremental_pause_usage.py`](../examples/incremental_pause_usage.py)
4. Integrate with hooks: See "Hook Integration" section in full docs

## API Summary

### IncrementalPauseManager

| Method | Purpose | Returns |
|--------|---------|---------|
| `is_pause_active()` | Check if pause is active | `bool` |
| `start_incremental_pause(%)` | Begin tracking | `session_id` |
| `append_action(type, data, %)` | Record action | `None` |
| `get_pause_summary()` | Get statistics | `dict` |
| `finalize_pause(snapshot?)` | Create snapshot | `Path` |
| `discard_pause()` | Abandon pause | `bool` |
| `get_recorded_actions()` | Read all actions | `List[PauseAction]` |

### PauseAction

```python
@dataclass
class PauseAction:
    type: str                    # Action type
    timestamp: str               # ISO format
    session_id: str              # Session ID
    data: dict                   # Action data
    context_percentage: float    # Context usage
```

## Quick Reference

### Start Pause
```python
session_id = manager.start_incremental_pause(0.90, initial_state)
```

### Record Action
```python
manager.append_action("tool_call", {"tool": "Read"}, 0.91)
```

### Finalize
```python
final_path = manager.finalize_pause()  # Full snapshot
# OR
archive = manager.finalize_pause(create_full_snapshot=False)  # JSONL only
```

### Discard
```python
manager.discard_pause()
```

---

**See Also:**
- [Full Documentation](./incremental-pause-workflow.md)
- [Implementation](../src/claude_mpm/services/cli/incremental_pause_manager.py)
- [Examples](../examples/incremental_pause_usage.py)
