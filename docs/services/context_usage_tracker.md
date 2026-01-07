# Context Usage Tracker Service

**Location**: `src/claude_mpm/services/infrastructure/context_usage_tracker.py`

## Overview

The `ContextUsageTracker` service provides cumulative token/context usage tracking across multiple Claude Code hook invocations. It enables intelligent auto-pause behavior by monitoring when the 200k context budget is being exhausted.

## Why This Service Exists

Claude Code hooks run in **separate processes**, making in-memory state tracking impossible. The `ContextUsageTracker` solves this by:

1. **File-based persistence** - State survives across hook invocations
2. **Atomic operations** - Safe concurrent access from multiple hooks
3. **Threshold detection** - Automatic warnings at 70%, 85%, 90%, 95% usage
4. **Auto-pause triggering** - Enables session pause at 90%+ context usage

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Claude Code Hook Invocation #1                          │
│   ├── ContextUsageTracker.update_usage(15k, 3k)        │
│   └── Persist to .claude-mpm/state/context-usage.json  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ (file-based state)
┌─────────────────────────────────────────────────────────┐
│ Claude Code Hook Invocation #2                          │
│   ├── Load cumulative state from file                   │
│   ├── ContextUsageTracker.update_usage(25k, 8k)        │
│   └── Persist updated state (40k input, 11k output)    │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼ (continues across invocations)
```

## Data Model

### ContextUsageState

```python
@dataclass
class ContextUsageState:
    session_id: str
    cumulative_input_tokens: int = 0
    cumulative_output_tokens: int = 0
    cache_creation_tokens: int = 0
    cache_read_tokens: int = 0
    percentage_used: float = 0.0  # 0.0 - 100.0
    threshold_reached: Optional[str] = None  # 'caution' | 'warning' | 'auto_pause' | 'critical'
    auto_pause_active: bool = False
    last_updated: str = ""  # ISO 8601 timestamp
```

### Thresholds

| Threshold | Percentage | Tokens (200k budget) | Action |
|-----------|-----------|---------------------|--------|
| `caution` | 70% | 140,000 | Yellow warning |
| `warning` | 85% | 170,000 | Orange warning |
| `auto_pause` | 90% | 180,000 | **Trigger auto-pause** |
| `critical` | 95% | 190,000 | Red critical alert |

## Usage

### Basic Usage

```python
from claude_mpm.services.infrastructure import ContextUsageTracker

# Initialize (uses current working directory as project root)
tracker = ContextUsageTracker()

# Update after API response
state = tracker.update_usage(
    input_tokens=15000,
    output_tokens=3000,
    cache_creation=5000,  # Optional
    cache_read=2000       # Optional
)

# Check if auto-pause should trigger
if tracker.should_auto_pause():
    # Trigger session pause workflow
    print("⚠️ Context budget at 90%+ - auto-pausing session")
    # ... create pause session ...
```

### Integration with Claude Code Hooks

```python
# In hook_pre_exit.py
from claude_mpm.services.infrastructure import ContextUsageTracker

def pre_exit_hook(hook_data: dict) -> None:
    """Update context usage from API response."""
    tracker = ContextUsageTracker()

    # Extract token counts from API response
    usage = hook_data.get("usage", {})
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_creation = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    # Update cumulative tracking
    state = tracker.update_usage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation=cache_creation,
        cache_read=cache_read
    )

    # Log threshold warnings
    if state.threshold_reached:
        log_threshold_warning(state)

    # Trigger auto-pause if needed
    if tracker.should_auto_pause():
        trigger_auto_pause(state)
```

### Checking Current State

```python
# Get current state without modifying
state = tracker.get_current_state()

print(f"Usage: {state.percentage_used:.1f}%")
print(f"Total tokens: {state.cumulative_input_tokens + state.cumulative_output_tokens}")
print(f"Threshold: {state.threshold_reached or 'None'}")
```

### Getting Usage Summary

```python
summary = tracker.get_usage_summary()

# Returns:
# {
#     "session_id": "session-20260106-123456",
#     "total_tokens": 143000,
#     "budget": 200000,
#     "percentage_used": 71.5,
#     "threshold_reached": "caution",
#     "auto_pause_active": False,
#     "breakdown": {
#         "input_tokens": 110000,
#         "output_tokens": 33000,
#         "cache_creation_tokens": 5000,
#         "cache_read_tokens": 3000
#     },
#     "last_updated": "2026-01-06T12:34:56.789Z"
# }
```

### Session Management

```python
# Reset tracking for new session
tracker.reset_session("session-20260106-153000")

# Creates fresh state:
# - All token counters → 0
# - percentage_used → 0.0
# - threshold_reached → None
# - auto_pause_active → False
```

## File Persistence

### State File Location

```
<project_root>/.claude-mpm/state/context-usage.json
```

### State File Format

```json
{
  "session_id": "session-20260106-123456",
  "cumulative_input_tokens": 110000,
  "cumulative_output_tokens": 33000,
  "cache_creation_tokens": 5000,
  "cache_read_tokens": 3000,
  "percentage_used": 71.5,
  "threshold_reached": "caution",
  "auto_pause_active": false,
  "last_updated": "2026-01-06T12:34:56.789Z"
}
```

### Atomic Operations

State updates use **atomic file operations** via `StateStorage`:

1. Write to temporary file: `.context-usage_XXXXX.tmp`
2. Compute SHA256 checksum
3. Atomic rename to `context-usage.json`

This prevents corruption from concurrent writes or interrupted operations.

## Error Handling

### Corrupted State File

If state file is corrupted or invalid JSON:

```python
# Tracker automatically recovers with default state
tracker = ContextUsageTracker()
state = tracker.get_current_state()

# Returns default state:
# - session_id: "session-<timestamp>"
# - All counters: 0
# - percentage_used: 0.0
```

### Missing State File

On first use, tracker creates default state automatically:

```python
tracker = ContextUsageTracker()
# Creates .claude-mpm/state/context-usage.json with defaults
```

### Invalid Token Counts

Negative token counts raise `ValueError`:

```python
try:
    tracker.update_usage(input_tokens=-100, output_tokens=200)
except ValueError as e:
    # Raises: "Token counts cannot be negative"
    pass
```

## Performance Considerations

### File I/O Overhead

Each `update_usage()` call:
1. Reads state file (~1-2 KB)
2. Updates counters in memory
3. Writes state file atomically

**Estimated time**: 1-5 milliseconds per update

**Recommendation**: Call once per hook invocation (not per API call within a hook).

### Concurrent Access

Multiple hooks can update state safely:
- Uses `fcntl` file locking on Unix/Linux/macOS
- Falls back to atomic writes on Windows
- Max retry attempts: 50 (5 second timeout)

## Testing

### Unit Tests

**Location**: `tests/services/infrastructure/test_context_usage_tracker.py`

**Coverage**: 26 tests covering:
- State initialization and defaults
- Cumulative token tracking
- Threshold detection (70%, 85%, 90%, 95%)
- Auto-pause triggering
- File persistence and atomic operations
- Corrupted state recovery
- Session reset
- Concurrent updates

**Run tests**:
```bash
pytest tests/services/infrastructure/test_context_usage_tracker.py -v
```

### Example Demo

**Location**: `examples/context_usage_tracker_example.py`

**Run demo**:
```bash
python examples/context_usage_tracker_example.py
```

Output shows:
- Simulated hook invocations with token updates
- Cumulative usage tracking
- Threshold detection
- Usage summary breakdown
- Session reset

## Integration Points

### Claude Code Hooks

**Primary Integration**: `hook_pre_exit.py`

```python
# Extract token usage from hook_data
usage = hook_data.get("usage", {})

# Update tracker
tracker.update_usage(
    input_tokens=usage.get("input_tokens", 0),
    output_tokens=usage.get("output_tokens", 0),
    cache_creation=usage.get("cache_creation_input_tokens", 0),
    cache_read=usage.get("cache_read_input_tokens", 0)
)
```

### Session Pause Manager

**Integration**: Trigger auto-pause when 90%+ reached

```python
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager
from claude_mpm.services.infrastructure import ContextUsageTracker

tracker = ContextUsageTracker()

if tracker.should_auto_pause():
    # Create pause session
    pause_manager = SessionPauseManager()
    session_id = pause_manager.create_pause_session(
        message=f"Auto-pause triggered at {tracker.get_current_state().percentage_used:.1f}% context usage"
    )
    print(f"Session paused: {session_id}")
```

### Dashboard/Monitoring

**Display usage metrics**:

```python
summary = tracker.get_usage_summary()

# Show in dashboard:
# - Progress bar: summary["percentage_used"]
# - Token count: summary["total_tokens"] / summary["budget"]
# - Threshold alert: summary["threshold_reached"]
# - Auto-pause status: summary["auto_pause_active"]
```

## API Reference

### ContextUsageTracker

#### `__init__(project_path: Optional[Path] = None)`

Initialize tracker with persistence path.

**Args**:
- `project_path`: Project root (default: current working directory)

**Example**:
```python
tracker = ContextUsageTracker()  # Uses cwd
tracker = ContextUsageTracker(Path("/path/to/project"))  # Custom path
```

---

#### `update_usage(input_tokens: int, output_tokens: int, cache_creation: int = 0, cache_read: int = 0) -> ContextUsageState`

Update cumulative usage from API response.

**Args**:
- `input_tokens`: Input tokens from this API call
- `output_tokens`: Output tokens from this API call
- `cache_creation`: Cache creation tokens (optional)
- `cache_read`: Cache read tokens (optional)

**Returns**: Updated `ContextUsageState`

**Raises**: `ValueError` if any token count is negative

**Example**:
```python
state = tracker.update_usage(15000, 3000)
state = tracker.update_usage(20000, 5000, cache_read=2000)
```

---

#### `should_auto_pause() -> bool`

Check if auto-pause should be triggered (90%+ usage).

**Returns**: `True` if at or above auto-pause threshold

**Example**:
```python
if tracker.should_auto_pause():
    # Trigger pause workflow
    pass
```

---

#### `check_thresholds(state: Optional[ContextUsageState] = None) -> Optional[str]`

Get highest threshold currently exceeded.

**Args**:
- `state`: Optional state to check (uses current if None)

**Returns**: `'caution'` | `'warning'` | `'auto_pause'` | `'critical'` | `None`

**Example**:
```python
threshold = tracker.check_thresholds()
if threshold == "critical":
    print("⚠️ Critical: 95%+ context usage")
```

---

#### `get_current_state() -> ContextUsageState`

Get current state without modifying.

**Returns**: Current `ContextUsageState`

**Example**:
```python
state = tracker.get_current_state()
print(f"Usage: {state.percentage_used:.1f}%")
```

---

#### `reset_session(new_session_id: str) -> None`

Reset tracking for new session.

**Args**:
- `new_session_id`: New session identifier

**Example**:
```python
tracker.reset_session("session-20260106-153000")
```

---

#### `get_usage_summary() -> dict`

Get formatted usage summary with breakdown.

**Returns**: Dictionary with usage statistics (see "Getting Usage Summary" above)

**Example**:
```python
summary = tracker.get_usage_summary()
print(f"Total: {summary['total_tokens']:,} tokens")
```

## Design Decisions

### Why File-Based Persistence?

**Problem**: Claude Code hooks run in separate processes, making shared in-memory state impossible.

**Solution**: File-based state in `.claude-mpm/state/` enables:
- State survival across hook invocations
- Cross-process state sharing
- Session resumption after crashes

### Why Atomic Operations?

**Problem**: Concurrent hooks could corrupt state file with partial writes.

**Solution**: Atomic write-to-temp-then-rename prevents corruption:
- Temp file written completely
- Checksum computed
- Atomic rename (OS-level operation)
- No partial writes visible

### Why Cache Tokens Tracked Separately?

**Problem**: Cache read tokens are "free" (don't count toward context budget), but cache creation does.

**Solution**: Track separately for accurate accounting:
- `cumulative_input_tokens + cumulative_output_tokens` → total effective usage
- `cache_read_tokens` → tracked but not counted in percentage
- `cache_creation_tokens` → tracked for observability

### Why 90% Auto-Pause Threshold?

**Problem**: Context exhaustion at 100% causes errors and poor responses.

**Solution**: 90% threshold provides:
- 20k token buffer for graceful pause
- Time to create pause session document
- Safety margin for final hook invocations

## Future Enhancements

### Token Budget Forecasting

Predict when auto-pause will trigger:

```python
# Estimate tokens remaining at current burn rate
tokens_per_hook = tracker.get_average_tokens_per_update()
hooks_until_pause = (200000 * 0.9 - current_usage) / tokens_per_hook
```

### Per-Session Analytics

Track token efficiency metrics:

```python
# Average tokens per task
# Peak usage periods
# Cache hit rate
analytics = tracker.get_session_analytics()
```

### Multi-Session History

Store historical sessions for trend analysis:

```python
# Track usage patterns over time
# Identify high-cost operations
# Optimize hook efficiency
history = tracker.get_usage_history(days=30)
```

## Troubleshooting

### State File Not Updating

**Symptom**: `update_usage()` returns stale values

**Check**:
1. File permissions on `.claude-mpm/state/`
2. Disk space availability
3. File locking conflicts (check logs)

**Fix**:
```bash
# Reset state file
rm .claude-mpm/state/context-usage.json
```

### Auto-Pause Not Triggering

**Symptom**: Usage exceeds 90% but auto-pause doesn't activate

**Check**:
1. `should_auto_pause()` return value
2. Hook integration calling tracker
3. `auto_pause_active` flag in state

**Debug**:
```python
state = tracker.get_current_state()
print(f"Usage: {state.percentage_used}%")
print(f"Auto-pause active: {state.auto_pause_active}")
print(f"Should pause: {tracker.should_auto_pause()}")
```

### Corrupted State File

**Symptom**: JSON parse errors in logs

**Fix**: Delete and recreate:
```bash
rm .claude-mpm/state/context-usage.json
# Tracker auto-creates default state on next use
```

## Related Services

- **SessionPauseManager** (`src/claude_mpm/services/cli/session_pause_manager.py`)
  - Creates pause sessions when auto-pause triggers
  - Documents context for resumption

- **StateStorage** (`src/claude_mpm/storage/state_storage.py`)
  - Provides atomic file operations
  - Handles file locking and checksums

## References

- [Claude API Documentation - Token Counting](https://docs.anthropic.com/claude/reference/tokens)
- [Incremental Pause Workflow](../incremental-pause-workflow.md)
- [Hook System](../developer/pretool-use-hooks.md)
