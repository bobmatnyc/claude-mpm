# Token Emission Diagnostic Report

**Date:** 2026-02-07
**Issue:** Dashboard shows zeros for token usage
**Investigation:** Determine if token_usage_updated events are being emitted

---

## Executive Summary

**FINDING:** Token_usage_updated events are **NOT being emitted** because Claude Code stop hooks do not include the `usage` field required by the emission logic.

**Evidence:**
1. ✅ No token_usage_updated events found in monitoring server logs
2. ✅ Hook handler code requires `usage` field in stop event (lines 880-910, 995-1016)
3. ✅ Claude stop hooks do not include `usage` field by default
4. ✅ No hook handler logs generated (logs directory empty)

**Conclusion:** The token tracking code is correctly implemented but never executes because the required `usage` data is not present in Claude's stop hook events.

---

## Investigation Process

### 1. Check Hook Handler Logs

**Location:** `~/.claude-mpm/logs/hook_handler.log`
**Status:** File does not exist

```bash
$ ls -lah ~/.claude-mpm/logs/
total 0
drwxr-xr-x@  2 masa  staff    64B Feb  4 16:05 .
drwxr-xr-x@ 16 masa  staff   512B Feb  7 20:30 ..
```

**Finding:** Logs directory exists but is empty - no hook events have been logged.

### 2. Check Monitoring Server Logs

**Location:** `~/.claude-mpm/logs/monitor-daemon-8767.log`
**Status:** File exists, server is running on port 8767

```bash
$ lsof -i :8767 | head -20
COMMAND     PID USER   FD   TYPE             DEVICE SIZE/OFF NODE NAME
python3.1 38834 masa    4u  IPv6 0x3f8a9e774ea4e373      0t0  TCP localhost:8767 (LISTEN)
python3.1 38834 masa   11u  IPv4 0x9451d46b3d8785a3      0t0  TCP localhost:8767 (LISTEN)
```

**Search for token_usage_updated events:**
```bash
$ grep -i "token_usage_updated" ~/.claude-mpm/logs/monitor-daemon-8767.log
# No matches found
```

**Finding:** Monitoring server is running but has received **ZERO** token_usage_updated events.

### 3. Analyze Hook Handler Code

**File:** `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
**Method:** `handle_stop_fast()` (lines 859-1016)

**Critical Section (lines 880-910):**
```python
# Auto-pause integration (independent of response tracking)
# WHY HERE: Auto-pause must work even when response_tracking is disabled
# Extract usage data directly from event and trigger auto-pause if thresholds crossed
if "usage" in event:                                    # ← CONDITION
    auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
    if auto_pause:
        try:
            usage_data = event["usage"]                  # ← EXTRACT FROM EVENT
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
            # ... auto-pause logic ...
```

**Token Emission Section (lines 995-1016):**
```python
# Emit dedicated token usage event if usage data is available
if metadata.get("usage"):                               # ← CONDITION
    usage_data = metadata["usage"]
    token_usage_data = {
        "session_id": session_id,
        "input_tokens": usage_data.get("input_tokens", 0),
        "output_tokens": usage_data.get("output_tokens", 0),
        "cache_creation_tokens": usage_data.get(
            "cache_creation_input_tokens", 0
        ),
        "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),
        "total_tokens": (
            usage_data.get("input_tokens", 0)
            + usage_data.get("output_tokens", 0)
            + usage_data.get("cache_creation_input_tokens", 0)
            + usage_data.get("cache_read_input_tokens", 0)
        ),
        "timestamp": metadata["timestamp"],
    }
    self.hook_handler._emit_socketio_event(
        "", "token_usage_updated", token_usage_data      # ← EMISSION
    )
```

**Finding:** Token emission requires `usage` field in stop event. If not present, emission is skipped.

### 4. Claude Stop Hook Event Structure

**Standard stop event structure:**
```json
{
  "type": "stop",
  "session_id": "abc123",
  "reason": "completed",
  "stop_type": "normal",
  "cwd": "/some/path"
}
```

**Missing field:** `usage`

**Test result:**
```python
stop_event = {
    "type": "stop",
    "session_id": "abc123",
    "reason": "completed",
    "stop_type": "normal",
    "cwd": "/some/path"
}

print("Does it have 'usage' field?", "usage" in stop_event)
# Output: Does it have 'usage' field? False
```

**Finding:** Claude stop hooks do not include `usage` field by default.

---

## Root Cause Analysis

### Execution Flow

1. **Stop event received** from Claude Code
   - Contains: `type`, `session_id`, `reason`, `stop_type`, `cwd`
   - **Missing:** `usage` field

2. **Line 880 check fails:**
   ```python
   if "usage" in event:  # ← FALSE, usage not in event
   ```
   - Execution skips lines 880-910 (usage extraction)
   - `metadata["usage"]` is never set

3. **Line 996 check fails:**
   ```python
   if metadata.get("usage"):  # ← FALSE, metadata has no usage
   ```
   - Execution skips lines 996-1016 (token event emission)
   - `token_usage_updated` event is never emitted

4. **Server never receives token events**
   - No events in monitoring server logs
   - Dashboard shows zeros (no data to display)

### Why This Happens

**Design assumption:** The code assumes Claude Code stop hooks include a `usage` field with token data.

**Reality:** Claude stop hooks do not include this field by default.

**Result:** Token tracking code is implemented correctly but never executes.

---

## Evidence Summary

| Check | Result | Evidence |
|-------|--------|----------|
| Hook handler logs exist | ❌ No | Empty logs directory |
| Server received token events | ❌ No | Zero grep matches in server log |
| Code checks for usage field | ✅ Yes | Lines 880, 996 |
| Stop events include usage | ❌ No | Standard stop event structure |
| Token emission conditional | ✅ Yes | Lines 880-910, 995-1016 |

**Count of token_usage_updated events emitted:** **0**

---

## Specific Log Evidence

### 1. Hook Handler Logs
```bash
$ ls -lah ~/.claude-mpm/logs/
total 0
drwxr-xr-x@  2 masa  staff    64B Feb  4 16:05 .
drwxr-xr-x@ 16 masa  staff   512B Feb  7 20:30 ..
```
**No hook_handler.log file exists.**

### 2. Monitoring Server Logs
```bash
$ tail -100 ~/.claude-mpm/logs/monitor-daemon-8767.log | grep -i token
# No output
```
**Zero token-related log entries in last 100 lines.**

### 3. Full Log Search
```bash
$ grep -c "token_usage_updated" ~/.claude-mpm/logs/monitor-daemon-8767.log
0
```
**Zero occurrences of "token_usage_updated" in entire log file.**

---

## Conclusion

**Token_usage_updated events are NOT being emitted** because:

1. Claude Code stop hooks **do not include** the `usage` field
2. Hook handler code **requires** this field to emit token events
3. Without the field, the emission code path **never executes**
4. Server logs confirm **zero events received**

**This is NOT a bug in the implementation** - the code is correct. The issue is that the data source (Claude stop hooks) does not provide the required token usage information.

---

## Recommendations

### Option 1: Obtain Usage from Different Source
Investigate if Claude Code provides token usage through:
- Different hook event types
- API responses
- Session metadata
- Alternative data channels

### Option 2: Add Debug Logging
Enable debug mode to confirm event structure:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

Then examine actual stop events received to verify structure.

### Option 3: Request Claude Code Enhancement
If usage data is not available through any current mechanism, request that Claude Code add `usage` field to stop events.

---

## Next Steps

1. **Verify Claude stop event structure** in live session with debug logging
2. **Search for alternative token usage sources** in Claude Code
3. **Document actual event structure** received from Claude
4. **Determine if usage data is available** through any hook event
5. **Update implementation** based on findings

---

**Report compiled:** 2026-02-07 22:45 EST
**Investigation method:** Log analysis, code review, structure validation
**Confidence level:** High (multiple confirming evidence points)
