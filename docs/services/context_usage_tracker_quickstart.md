# Context Usage Tracker - Quick Start Guide

## Installation

No installation needed - service is part of `claude_mpm.services.infrastructure`.

## Basic Usage (30 seconds)

```python
from claude_mpm.services.infrastructure import ContextUsageTracker

# Initialize tracker
tracker = ContextUsageTracker()

# Update from API response
state = tracker.update_usage(
    input_tokens=15000,
    output_tokens=3000
)

# Check usage
print(f"Usage: {state.percentage_used:.1f}%")

# Check if auto-pause needed
if tracker.should_auto_pause():
    print("⚠️ Auto-pause triggered at 90%+")
```

## Common Scenarios

### Scenario 1: Hook Integration

```python
# In hook_pre_exit.py
def pre_exit_hook(hook_data: dict):
    tracker = ContextUsageTracker()
    usage = hook_data.get("usage", {})

    state = tracker.update_usage(
        input_tokens=usage.get("input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        cache_read=usage.get("cache_read_input_tokens", 0)
    )

    # Log threshold warnings
    if state.threshold_reached:
        logger.warning(f"Threshold reached: {state.threshold_reached}")

    # Trigger auto-pause
    if tracker.should_auto_pause():
        create_pause_session(state)
```

### Scenario 2: Get Current Status

```python
tracker = ContextUsageTracker()
state = tracker.get_current_state()

print(f"Session: {state.session_id}")
print(f"Usage: {state.percentage_used:.1f}%")
print(f"Threshold: {state.threshold_reached or 'None'}")
print(f"Auto-pause: {state.auto_pause_active}")
```

### Scenario 3: Usage Summary

```python
summary = tracker.get_usage_summary()

print(f"Total: {summary['total_tokens']:,} / {summary['budget']:,}")
print(f"Usage: {summary['percentage_used']:.2f}%")
print(f"Input: {summary['breakdown']['input_tokens']:,}")
print(f"Output: {summary['breakdown']['output_tokens']:,}")
```

### Scenario 4: Reset Session

```python
# Start fresh tracking for new session
tracker.reset_session("session-20260106-153000")

# All counters reset to 0
state = tracker.get_current_state()
assert state.percentage_used == 0.0
```

## Threshold Levels

| Level | Usage | Action |
|-------|-------|--------|
| Caution | 70% | Yellow warning ⚠️ |
| Warning | 85% | Orange warning 🟠 |
| Auto-Pause | 90% | **Trigger pause** 🛑 |
| Critical | 95% | Red alert 🔴 |

## State File Location

```
<project>/.claude-mpm/state/context-usage.json
```

**Format**: JSON with atomic writes

**Persistence**: Survives across hook invocations

## Error Handling

### Corrupted State File

```python
# Automatically recovers with default state
tracker = ContextUsageTracker()
# Creates fresh state if file corrupted
```

### Missing State File

```python
# Creates default state on first use
tracker = ContextUsageTracker()
# Auto-generates session ID
```

### Invalid Token Counts

```python
try:
    tracker.update_usage(input_tokens=-100, output_tokens=200)
except ValueError:
    # Raises: "Token counts cannot be negative"
    pass
```

## Testing

```bash
# Run tests
pytest tests/services/infrastructure/test_context_usage_tracker.py -v

# Run example
python examples/context_usage_tracker_example.py

# Import validation
python -c "from claude_mpm.services.infrastructure import ContextUsageTracker; print('✓')"
```

## Key Methods

| Method | Purpose | Returns |
|--------|---------|---------|
| `update_usage(input, output)` | Add tokens from API call | `ContextUsageState` |
| `should_auto_pause()` | Check if 90%+ usage | `bool` |
| `get_current_state()` | Get state without modifying | `ContextUsageState` |
| `get_usage_summary()` | Get formatted statistics | `dict` |
| `reset_session(id)` | Reset for new session | `None` |
| `check_thresholds()` | Get highest threshold exceeded | `str | None` |

## Example Output

```
Usage: 71.5%
Total: 143,000 / 200,000 tokens
Threshold: caution
Auto-pause: False

Breakdown:
  Input:  110,000
  Output:  33,000
  Cache:    5,000
```

## Integration Points

1. **Claude Code Hooks** - `hook_pre_exit.py` updates usage
2. **Session Pause Manager** - Auto-pause at 90%+
3. **Dashboard** - Display progress bars and alerts
4. **Monitoring** - Track usage trends

## Troubleshooting

### Usage not updating?

```bash
# Check state file
cat .claude-mpm/state/context-usage.json

# Verify permissions
ls -la .claude-mpm/state/
```

### Auto-pause not triggering?

```python
# Debug threshold check
state = tracker.get_current_state()
print(f"Usage: {state.percentage_used}%")
print(f"Should pause: {tracker.should_auto_pause()}")
```

### State file corrupted?

```bash
# Delete and recreate
rm .claude-mpm/state/context-usage.json
# Tracker auto-creates on next use
```

## Full Documentation

See: `docs/services/context_usage_tracker.md`

## Example Code

See: `examples/context_usage_tracker_example.py`

## Tests

See: `tests/services/infrastructure/test_context_usage_tracker.py`
