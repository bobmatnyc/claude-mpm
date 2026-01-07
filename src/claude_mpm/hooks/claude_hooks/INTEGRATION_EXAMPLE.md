# Auto-Pause Handler Integration Example

This document shows how to integrate the `AutoPauseHandler` with the existing `response_tracking.py` hook handler.

## Integration Steps

### 1. Initialize Handler in ResponseTrackingManager

Add to `response_tracking.py` around line 30:

```python
from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler

class ResponseTrackingManager:
    """Manager for response tracking functionality."""

    def __init__(self):
        self.response_tracker: Optional[Any] = None
        self.response_tracking_enabled = False
        self.track_all_interactions = False

        # Initialize auto-pause handler
        self.auto_pause_handler: Optional[AutoPauseHandler] = None
        self._initialize_auto_pause()

        if RESPONSE_TRACKING_AVAILABLE:
            self._initialize_response_tracking()

    def _initialize_auto_pause(self):
        """Initialize auto-pause handler for context management."""
        try:
            self.auto_pause_handler = AutoPauseHandler()

            if DEBUG:
                status = self.auto_pause_handler.get_status()
                print(
                    f"✅ Auto-pause handler initialized: "
                    f"{status['context_percentage']}% context used",
                    file=sys.stderr
                )
        except Exception as e:
            if DEBUG:
                print(f"❌ Failed to initialize auto-pause handler: {e}", file=sys.stderr)
            # Don't fail - auto-pause is optional
```

### 2. Monitor Token Usage in track_stop_response()

Add to `track_stop_response()` method around line 327 (after capturing usage data):

```python
def track_stop_response(
    self, event: dict, session_id: str, metadata: dict, pending_prompts: dict
):
    """Track response for stop events.

    Captures Claude API stop_reason and usage data for context management.
    """
    if not (self.response_tracking_enabled and self.response_tracker):
        return

    try:
        # ... existing code ...

        # Capture Claude API usage data if available
        if "usage" in event:
            usage_data = event["usage"]
            metadata["usage"] = {
                "input_tokens": usage_data.get("input_tokens", 0),
                "output_tokens": usage_data.get("output_tokens", 0),
                "cache_creation_input_tokens": usage_data.get(
                    "cache_creation_input_tokens", 0
                ),
                "cache_read_input_tokens": usage_data.get(
                    "cache_read_input_tokens", 0
                ),
            }

            # ===== NEW: Auto-pause integration =====
            if self.auto_pause_handler:
                threshold_crossed = self.auto_pause_handler.on_usage_update(
                    metadata["usage"]
                )

                if threshold_crossed:
                    warning = self.auto_pause_handler.emit_threshold_warning(
                        threshold_crossed
                    )
                    print(f"\n⚠️  {warning}", file=sys.stderr)
            # ===== END NEW =====

            if DEBUG:
                total_tokens = usage_data.get(
                    "input_tokens", 0
                ) + usage_data.get("output_tokens", 0)
                print(
                    f"  - Captured usage: {total_tokens} total tokens",
                    file=sys.stderr,
                )

        # ... rest of existing code ...
```

### 3. Record Actions During Pause Mode

Add to tool call tracking (in the main hook handler where tools are processed):

```python
# When a tool is called
if self.auto_pause_handler and self.auto_pause_handler.is_pause_active():
    self.auto_pause_handler.on_tool_call(tool_name, tool_args)
```

Add to assistant response tracking:

```python
# When assistant responds
if self.auto_pause_handler and self.auto_pause_handler.is_pause_active():
    # Summarize response to avoid storing full content
    summary = response[:200] + "..." if len(response) > 200 else response
    self.auto_pause_handler.on_assistant_response(summary)
```

### 4. Finalize Session on End

Add to session cleanup/end handler:

```python
def on_session_end(self):
    """Handle session end."""
    if self.auto_pause_handler:
        session_file = self.auto_pause_handler.on_session_end()

        if session_file and DEBUG:
            print(f"✅ Session finalized: {session_file}", file=sys.stderr)
```

## Testing the Integration

### Test 1: Verify Initialization

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
# Run Claude Code - check stderr for initialization message:
# "✅ Auto-pause handler initialized: 0.0% context used"
```

### Test 2: Simulate Threshold Crossing

You can test manually by modifying the context usage state file:

```bash
# View current state
cat .claude-mpm/state/context-usage.json

# Or check status programmatically
python -c "
from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler
handler = AutoPauseHandler()
print(handler.get_status())
"
```

### Test 3: Verify Action Recording

After auto-pause is triggered:

```bash
# Check for active pause file
ls -la .claude-mpm/sessions/ACTIVE-PAUSE.jsonl

# View recorded actions
cat .claude-mpm/sessions/ACTIVE-PAUSE.jsonl | jq .
```

### Test 4: Finalize and Check Output

```bash
# After session ends, check for finalized session files
ls -la .claude-mpm/sessions/session-*.json
ls -la .claude-mpm/sessions/session-*.yaml
ls -la .claude-mpm/sessions/session-*.md
```

## Expected Behavior

1. **At 70% context usage**: Caution warning emitted
2. **At 85% context usage**: Warning emitted
3. **At 90% context usage**:
   - Auto-pause triggered
   - `ACTIVE-PAUSE.jsonl` created
   - Actions recorded incrementally
4. **At 95% context usage**: Critical warning emitted
5. **On session end**:
   - Pause finalized
   - Session files created (JSON, YAML, MD)
   - `ACTIVE-PAUSE.jsonl` archived

## Debug Output Examples

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

## Error Handling

The integration is designed to be resilient:

- Auto-pause failures don't break the main hook flow
- All errors are logged to stderr in DEBUG mode
- Missing dependencies are handled gracefully
- Invalid state files trigger default initialization

## Monitoring

Check auto-pause status programmatically:

```python
from claude_mpm.hooks.claude_hooks.auto_pause_handler import AutoPauseHandler

handler = AutoPauseHandler()
status = handler.get_status()

print(f"Context: {status['context_percentage']}%")
print(f"Threshold: {status['threshold_reached']}")
print(f"Pause active: {status['pause_active']}")

if status.get('pause_details'):
    print(f"Actions recorded: {status['pause_details']['action_count']}")
```
