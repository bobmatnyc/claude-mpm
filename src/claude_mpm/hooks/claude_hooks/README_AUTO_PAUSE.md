# Auto-Pause Handler for Claude Code Hooks

## Overview

The **AutoPauseHandler** component automatically pauses Claude sessions when context usage reaches 90% of the 200k token budget. It integrates seamlessly with Claude Code hooks to monitor API responses, track cumulative token usage, and capture actions during the "wind-down" period before the session ends.

## Key Features

- **Automatic threshold detection** at 70%, 85%, 90%, and 95% context usage
- **Auto-pause triggering** when 90%+ budget consumed
- **Incremental action capture** during pause mode (tool calls, responses, messages)
- **Thread-safe file-based persistence** across hook process restarts
- **User-friendly warnings** emitted to stderr
- **Graceful error handling** - failures don't break main hook flow
- **No duplicate triggers** - only emits warnings on NEW threshold crossings

## Architecture

```
AutoPauseHandler
├── ContextUsageTracker      # Cumulative token tracking across API calls
│   ├── File: .claude-mpm/state/context-usage.json
│   └── Tracks: input/output tokens, cache tokens, thresholds
│
└── IncrementalPauseManager  # Captures actions during pause mode
    ├── File: .claude-mpm/sessions/ACTIVE-PAUSE.jsonl
    └── Captures: tool_call, assistant_response, user_message
```

## Usage

### 1. Initialize in Hook Handler

```python
from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler

class ResponseTrackingManager:
    def __init__(self):
        # Initialize auto-pause handler
        self.auto_pause_handler = AutoPauseHandler()
```

### 2. Monitor Token Usage

```python
def track_stop_response(self, event: dict, session_id: str, metadata: dict):
    """Track response for stop events."""
    if "usage" in event:
        usage_data = event["usage"]

        # Update token usage and check thresholds
        if self.auto_pause_handler:
            threshold_crossed = self.auto_pause_handler.on_usage_update(usage_data)

            if threshold_crossed:
                warning = self.auto_pause_handler.emit_threshold_warning(threshold_crossed)
                print(f"\n⚠️  {warning}", file=sys.stderr)
```

### 3. Record Actions During Pause

```python
# When a tool is called
if self.auto_pause_handler.is_pause_active():
    self.auto_pause_handler.on_tool_call(tool_name, tool_args)

# When assistant responds
if self.auto_pause_handler.is_pause_active():
    summary = response[:200] + "..." if len(response) > 200 else response
    self.auto_pause_handler.on_assistant_response(summary)

# When user sends message
if self.auto_pause_handler.is_pause_active():
    self.auto_pause_handler.on_user_message(message_text)
```

### 4. Finalize on Session End

```python
def on_session_end(self):
    """Handle session end."""
    if self.auto_pause_handler:
        session_file = self.auto_pause_handler.on_session_end()

        if session_file:
            print(f"✅ Session finalized: {session_file}", file=sys.stderr)
```

## API Reference

### `AutoPauseHandler`

#### `__init__(project_path: Optional[Path] = None)`

Initialize auto-pause handler.

**Args:**
- `project_path`: Project root path (default: current directory)

---

#### `on_usage_update(usage: Dict[str, Any]) -> Optional[str]`

Process token usage from a Claude API response.

**Args:**
- `usage`: Dict with `input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`

**Returns:**
- Threshold name if NEW threshold crossed: `"caution"`, `"warning"`, `"auto_pause"`, `"critical"`
- `None` if no new threshold crossed

**Example:**
```python
usage = {
    "input_tokens": 130000,
    "output_tokens": 52000,
    "cache_creation_input_tokens": 5000,
    "cache_read_input_tokens": 10000
}

threshold = handler.on_usage_update(usage)

if threshold == "auto_pause":
    print("Auto-pause triggered!")
```

---

#### `on_tool_call(tool_name: str, tool_args: Dict[str, Any]) -> None`

Record a tool call if auto-pause is active.

**Args:**
- `tool_name`: Name of the tool being called
- `tool_args`: Tool arguments dictionary

**Example:**
```python
handler.on_tool_call("Read", {"file_path": "/test/file.py", "limit": 100})
```

---

#### `on_assistant_response(response_summary: str) -> None`

Record an assistant response if auto-pause is active.

**Args:**
- `response_summary`: Summary of assistant response (truncated to 500 chars)

**Example:**
```python
handler.on_assistant_response("File modified successfully...")
```

---

#### `on_user_message(message_summary: str) -> None`

Record a user message if auto-pause is active.

**Args:**
- `message_summary`: Summary of user message (truncated to 500 chars)

**Example:**
```python
handler.on_user_message("Please fix the authentication bug.")
```

---

#### `on_session_end() -> Optional[Path]`

Finalize any active pause session.

**Returns:**
- `Path` to finalized session file, or `None` if no pause was active

**Example:**
```python
session_file = handler.on_session_end()

if session_file:
    print(f"Session saved to: {session_file}")
```

---

#### `is_pause_active() -> bool`

Check if auto-pause mode is currently active.

**Returns:**
- `True` if auto-pause has been triggered and is capturing actions

---

#### `get_status() -> Dict[str, Any]`

Get current status for display/logging.

**Returns:**
Dict with:
- `context_percentage`: Current context usage (0.0-100.0)
- `threshold_reached`: Highest threshold crossed or `None`
- `auto_pause_active`: Whether auto-pause has been triggered
- `pause_active`: Whether pause is currently recording actions
- `session_id`: Current session identifier
- `total_tokens`: Total tokens used (input + output)
- `budget`: Total context budget (200,000)
- `pause_details`: (if active) action_count, duration_seconds, context_range, last_action_type

**Example:**
```python
status = handler.get_status()

print(f"Context: {status['context_percentage']}%")
print(f"Threshold: {status['threshold_reached']}")
print(f"Pause active: {status['pause_active']}")

if status.get('pause_details'):
    print(f"Actions recorded: {status['pause_details']['action_count']}")
```

---

#### `emit_threshold_warning(threshold: str) -> str`

Generate a warning message for threshold crossing.

**Args:**
- `threshold`: Threshold name (`"caution"`, `"warning"`, `"auto_pause"`, `"critical"`)

**Returns:**
- User-friendly warning message string

**Example:**
```python
warning = handler.emit_threshold_warning("auto_pause")
# Returns: "Context usage at 90%. Auto-pause activated. Actions are being recorded for session continuity. (91.2%)"
```

## Threshold Levels

| Threshold | Percentage | Behavior |
|-----------|------------|----------|
| **Caution** | 70% | Warning emitted, no action taken |
| **Warning** | 85% | Stronger warning emitted, no action taken |
| **Auto-pause** | 90% | **Pause triggered**, actions recorded |
| **Critical** | 95% | Critical warning emitted, pause already active |

## Warning Messages

```python
THRESHOLD_WARNINGS = {
    "caution": "Context usage at 70%. Consider wrapping up current work.",
    "warning": "Context usage at 85%. Session nearing capacity.",
    "auto_pause": "Context usage at 90%. Auto-pause activated. Actions are being recorded for session continuity.",
    "critical": "Context usage at 95%. Session nearly exhausted. Wrapping up...",
}
```

## Output Files

When auto-pause is triggered, the following files are created:

### During Pause (Incremental Capture)

```
.claude-mpm/sessions/ACTIVE-PAUSE.jsonl
```

**Format:** JSONL (one JSON object per line)

**Example:**
```jsonl
{"type":"pause_started","timestamp":"2026-01-06T23:15:42.123Z","session_id":"session-20260106-151542","data":{"context_percentage":0.91,"initial_state":{...},"reason":"Auto-pause threshold exceeded (90%+)"},"context_percentage":0.91}
{"type":"tool_call","timestamp":"2026-01-06T23:15:45.456Z","session_id":"session-20260106-151542","data":{"tool":"Read","args_summary":{"file_path":"/test/file.py"}},"context_percentage":0.912}
{"type":"assistant_response","timestamp":"2026-01-06T23:15:48.789Z","session_id":"session-20260106-151542","data":{"summary":"File read successfully..."},"context_percentage":0.915}
```

### After Finalization

```
.claude-mpm/sessions/session-20260106-151542.json    # Full session state
.claude-mpm/sessions/session-20260106-151542.yaml    # Human-readable YAML
.claude-mpm/sessions/session-20260106-151542.md      # Markdown summary
.claude-mpm/sessions/session-20260106-151542-incremental.jsonl  # Archived JSONL
```

## State Persistence

### Context Usage State

**File:** `.claude-mpm/state/context-usage.json`

**Format:**
```json
{
  "session_id": "session-20260106-151542",
  "cumulative_input_tokens": 130000,
  "cumulative_output_tokens": 52000,
  "cache_creation_tokens": 5000,
  "cache_read_tokens": 10000,
  "percentage_used": 91.0,
  "threshold_reached": "auto_pause",
  "auto_pause_active": true,
  "last_updated": "2026-01-06T23:15:42.123Z"
}
```

This state persists across hook process restarts, enabling cumulative tracking.

## Testing

Run the comprehensive test suite:

```bash
python -m pytest tests/hooks/test_auto_pause_handler.py -v
```

**Test coverage:**
- ✅ Initialization and state loading
- ✅ Token usage updates and threshold detection
- ✅ Action recording during pause mode
- ✅ Session finalization and output files
- ✅ Status reporting and warnings
- ✅ Edge cases and error handling
- ✅ Concurrency and state persistence

## Debugging

Enable debug mode to see detailed logs:

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

**Expected debug output:**
```
✅ Auto-pause handler initialized: 0.0% context used
  - Captured usage: 15234 total tokens
Context threshold crossed: caution (72.3%)
⚠️  Context usage at 70%. Consider wrapping up current work. (72.3%)
  - Captured usage: 32451 total tokens
Context threshold crossed: warning (86.7%)
⚠️  Context usage at 85%. Session nearing capacity. (86.7%)
  - Captured usage: 45678 total tokens
Context threshold crossed: auto_pause (91.2%)
✅ Auto-pause triggered: session-20260106-143022 (91.2% context used)
⚠️  Context usage at 90%. Auto-pause activated. Actions are being recorded for session continuity. (91.2%)
Recorded tool call during pause: Read
Recorded assistant response during pause (length: 245)
✅ Session finalized: session-20260106-143022.json
```

## Integration Example

See `INTEGRATION_EXAMPLE.md` for complete integration guide with `response_tracking.py`.

## Error Handling

The handler is designed to be resilient:

- ✅ **No breaking failures**: All errors are caught and logged
- ✅ **Graceful degradation**: Missing dependencies handled gracefully
- ✅ **Invalid state recovery**: Corrupted files trigger default initialization
- ✅ **Thread-safe**: Atomic file operations prevent corruption
- ✅ **Optional feature**: Auto-pause failures don't break main hook flow

## Performance Characteristics

- **Overhead**: Minimal (~1-2ms per API call for state updates)
- **Storage**: ~1-5KB per session state file
- **Memory**: Constant (state persisted to disk, not held in memory)
- **Concurrency**: Safe (atomic file operations with locking)

## Limitations

1. **Token accuracy**: Relies on accurate token counts from Claude API
2. **Cross-session tracking**: Each session tracked independently (no cross-session cumulative tracking)
3. **Manual reset**: No automatic session reset (must manually delete state files)
4. **Summary truncation**: Long responses truncated to 500 chars (configurable via `MAX_SUMMARY_LENGTH`)

## Future Enhancements

- [ ] Add session reset command: `mpm reset-context`
- [ ] Support custom threshold percentages via config
- [ ] Add email/webhook notifications for critical thresholds
- [ ] Implement session resume from finalized pause files
- [ ] Add visualization dashboard for token usage trends

## Related Components

- **ContextUsageTracker**: Token tracking service (`src/claude_mpm/services/infrastructure/context_usage_tracker.py`)
- **IncrementalPauseManager**: Action capture service (`src/claude_mpm/services/cli/incremental_pause_manager.py`)
- **SessionPauseManager**: Session finalization service (`src/claude_mpm/services/cli/session_pause_manager.py`)
- **Response Tracking**: Hook integration (`src/claude_mpm/hooks/claude_hooks/response_tracking.py`)

## License

Part of Claude Multi-Agent Project Manager (MPM).
