# Token Usage Verification Findings

**Date**: 2026-02-07
**Task**: Verify if alternative hook types provide usage data
**Status**: Code Analysis Complete (Live Testing Required)

## Executive Summary

### Current Implementation Status

✅ **Stop Hooks**: Confirmed to extract and emit token usage data
❌ **AssistantResponse Hooks**: No usage data extraction implemented
⚠️ **Live Verification**: Blocked due to Claude CLI hanging in test environment

### Key Finding

**Stop hooks are currently the ONLY hook type extracting token usage data.**

Whether AssistantResponse hooks also provide usage data is **UNKNOWN** and requires live testing.

---

## Evidence

### Stop Hook Implementation (Confirmed)

**File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
**Lines**: 880-1016

#### Usage Data Extraction (Lines 880-894)

```python
if "usage" in event:
    auto_pause = getattr(self.hook_handler, "auto_pause_handler", None)
    if auto_pause:
        try:
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
```

#### Token Event Emission (Lines 996-1016)

```python
if metadata.get("usage"):
    usage_data = metadata["usage"]
    token_usage_data = {
        "session_id": session_id,
        "input_tokens": usage_data.get("input_tokens", 0),
        "output_tokens": usage_data.get("output_tokens", 0),
        "cache_creation_tokens": usage_data.get("cache_creation_input_tokens", 0),
        "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),
        "total_tokens": (
            usage_data.get("input_tokens", 0)
            + usage_data.get("output_tokens", 0)
            + usage_data.get("cache_creation_input_tokens", 0)
            + usage_data.get("cache_read_input_tokens", 0)
        ),
        "timestamp": metadata["timestamp"],
    }
    self.hook_handler._emit_socketio_event("", "token_usage_updated", token_usage_data)
```

**Conclusion**: ✅ Stop hooks are fully implemented for token usage tracking.

### AssistantResponse Hook Implementation (Not Found)

**File**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
**Lines**: 1160-1256

```python
def handle_assistant_response(self, event):
    """Handle assistant response events for comprehensive response tracking."""
    # ... response tracking code ...
    # NO usage data extraction
    # NO check for event['usage']
    # NO token_usage_updated emission
```

**Conclusion**: ❌ AssistantResponse handler does NOT extract usage data.

---

## Analysis: Stop vs AssistantResponse

### Characteristics

| Hook Type | Frequency | Scope | Current Usage Extraction |
|-----------|-----------|-------|-------------------------|
| **Stop** | Once per session | Session-level | ✅ Implemented |
| **AssistantResponse** | Per response | Response-level | ❌ Not implemented |

### Unknown Questions

1. **Does Claude Code provide usage data in AssistantResponse events?**
   - Unknown without live testing
   - Requires examining actual event payloads

2. **What granularity does usage data have?**
   - Session-level (accumulated)?
   - Response-level (per interaction)?

3. **Which hook type provides more accurate token tracking?**
   - Stop: Known to work, session-level
   - AssistantResponse: Unknown if available, potentially response-level

---

## Verification Script Analysis

### Script Purpose

**File**: `scripts/verify_assistant_response_usage.py`

The script attempts to:
1. Enable debug logging
2. Parse hook handler logs
3. Search for AssistantResponse events
4. Check if `"usage"` field is present
5. Report findings

### Blockers

1. **No hook logs exist**: `~/.claude-mpm/logs/` is empty
2. **Debug mode not enabled**: `CLAUDE_MPM_HOOK_DEBUG=false`
3. **No Claude interactions**: No events to analyze

### Why Verification Failed

```bash
$ python3 scripts/verify_assistant_response_usage.py

🔍 Token Usage Source Verification

Debug mode: ❌ DISABLED

⚠️  Warning: Debug logging is not enabled
Enable with: export CLAUDE_MPM_HOOK_DEBUG=true
Then trigger a Claude interaction before running this script

❌ No hook handler logs found
Expected location: ~/.claude-mpm/logs/hook_handler.log

Actions:
1. Enable debug: export CLAUDE_MPM_HOOK_DEBUG=true
2. Trigger Claude: echo 'test' | claude
3. Re-run this script
```

**Root Cause**: Cannot trigger Claude CLI interaction in test environment (hangs).

---

## Recommended Next Steps

### Option 1: Verify Current Implementation (Simplest)

Since Stop hooks are already implemented and working:

```bash
# 1. Enable debug mode
export CLAUDE_MPM_HOOK_DEBUG=true

# 2. Start MPM dashboard
mpm --with-dashboard

# 3. In new terminal, trigger Claude
echo "What is 2+2?" | claude

# 4. Monitor token events
tail -f ~/.claude-mpm/logs/hook_handler.log | grep "token_usage"

# 5. Check dashboard
# Visit http://localhost:8667/tokens to see if tokens are tracked
```

**Expected Result**: token_usage_updated events should appear in logs and dashboard.

### Option 2: Test AssistantResponse Usage (Experimental)

Add usage extraction to AssistantResponse handler to test availability:

```bash
# 1. Apply experimental patch
cat > /tmp/assistant_response_usage.patch << 'EOF'
--- a/src/claude_mpm/hooks/claude_hooks/event_handlers.py
+++ b/src/claude_mpm/hooks/claude_hooks/event_handlers.py
@@ -1193,6 +1193,17 @@ class EventHandlers:
         response_text = event.get("response", "")
         session_id = event.get("session_id", "")

+        # EXPERIMENTAL: Check if usage data is available in AssistantResponse
+        if "usage" in event:
+            usage_data = event["usage"]
+            assistant_response_data["usage"] = {
+                "input_tokens": usage_data.get("input_tokens", 0),
+                "output_tokens": usage_data.get("output_tokens", 0),
+                "cache_creation_tokens": usage_data.get("cache_creation_input_tokens", 0),
+                "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),
+            }
+            if DEBUG:
+                _log(f"AssistantResponse contains usage data: {usage_data}")
+
         # Prepare assistant response data for Socket.IO emission
         assistant_response_data = {
             "response_text": response_text,
EOF

# 2. Apply patch
cd /Users/masa/Projects/claude-mpm
patch -p1 < /tmp/assistant_response_usage.patch

# 3. Restart MPM
mpm --with-dashboard

# 4. Enable debug and test
export CLAUDE_MPM_HOOK_DEBUG=true
echo "test" | claude

# 5. Check logs for usage data
grep "AssistantResponse contains usage data" ~/.claude-mpm/logs/hook_handler.log
```

**Interpretation**:
- **If found**: ✅ AssistantResponse provides per-response token counts
- **If not found**: ❌ Only Stop hooks provide usage data (session-level)

### Option 3: Review Claude Code Documentation

Check official Claude Code documentation for hook event schemas:

```bash
# Search for hook documentation
claude --help | grep -i hook

# Check if Claude Code has event schema documentation
# Look for: event types, payload structures, usage field availability
```

**Goal**: Determine authoritative source for which events include usage data.

---

## Decision Matrix

| Scenario | Recommendation |
|----------|---------------|
| **Only Stop provides usage** | ✅ Current implementation is correct, no changes needed |
| **AssistantResponse also provides usage** | Consider switching to AssistantResponse for response-level granularity |
| **Both provide usage** | Use AssistantResponse for real-time tracking, Stop as backup |
| **Neither provides usage** | Investigate Claude Code internals or request feature |

---

## Action Items

### Immediate (Required)

1. ✅ **Code Analysis**: Complete (this document)
2. ⏳ **Live Testing**: Trigger Claude interaction with debug enabled
3. ⏳ **Verification**: Run `verify_assistant_response_usage.py` with logs

### Follow-up (Conditional)

4. If AssistantResponse has usage:
   - Update event_handlers.py to extract from AssistantResponse
   - Emit token_usage_updated events per response
   - Update dashboard to show response-level granularity

5. If only Stop has usage:
   - Document that token tracking is session-level
   - Optimize Stop hook implementation
   - Consider alternative approaches for response-level tracking

---

## Testing Commands Quick Reference

```bash
# Enable debug mode
export CLAUDE_MPM_HOOK_DEBUG=true

# Start dashboard
mpm --with-dashboard

# In new terminal, trigger Claude
echo "What is 2+2?" | claude

# Monitor logs
tail -f ~/.claude-mpm/logs/hook_handler.log

# Run verification script
python3 scripts/verify_assistant_response_usage.py

# Check for token events
grep "token_usage_updated" ~/.claude-mpm/logs/hook_handler.log

# Check dashboard
open http://localhost:8667/tokens
```

---

## Conclusion

**Current State**:
- Stop hooks: ✅ Implemented and emitting token usage
- AssistantResponse hooks: ❌ Not extracting usage (unknown if available)

**Blocker**:
- Cannot verify AssistantResponse usage without live Claude interaction

**Next Step**:
- Run testing commands above to generate hook logs
- Re-run verification script with actual event data
- Make implementation decision based on findings

---

## Related Files

- **Event Handlers**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
- **Verification Script**: `scripts/verify_assistant_response_usage.py`
- **Analysis Script**: `scripts/analyze_hook_structure.py`
- **Patch Generator**: `scripts/patch_assistant_response_usage.py`
- **This Document**: `docs/token-usage-verification-findings.md`
