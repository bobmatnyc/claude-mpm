# Token Usage Structure Mismatch - Side-by-Side Comparison

## Problem Statement
Dashboard shows zeros for all token counts even on fresh browser, indicating event structure mismatch.

---

## Server-Side Event Emission

### File: `event_handlers.py:859-1016` (handle_stop_fast)

**Step 1: Extract usage from stop event (lines 880-894)**
```python
if "usage" in event:
    usage_data = event["usage"]  # From Claude hook event
    metadata["usage"] = {
        "input_tokens": usage_data.get("input_tokens", 0),
        "output_tokens": usage_data.get("output_tokens", 0),
        "cache_creation_input_tokens": usage_data.get("cache_creation_input_tokens", 0),
        "cache_read_input_tokens": usage_data.get("cache_read_input_tokens", 0),
    }
```

**Step 2: Emit token_usage_updated event (lines 996-1016)**
```python
if metadata.get("usage"):
    usage_data = metadata["usage"]
    token_usage_data = {
        "session_id": session_id,
        "input_tokens": usage_data.get("input_tokens", 0),
        "output_tokens": usage_data.get("output_tokens", 0),
        "cache_creation_tokens": usage_data.get("cache_creation_input_tokens", 0),  # ← KEY MAPPING
        "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),         # ← KEY MAPPING
        "total_tokens": (...),
        "timestamp": metadata["timestamp"],
    }
    self.hook_handler._emit_socketio_event("", "token_usage_updated", token_usage_data)
```

### File: `connection_manager_http.py:93-135` (emit_event)

**Step 3: Wrap in normalized event structure**
```python
raw_event = {
    "type": "hook",
    "subtype": "token_usage_updated",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "data": token_usage_data,  # The dict from above
    "source": "claude_hooks",
    "session_id": data.get("session_id") or data.get("sessionId"),
}
normalized_event = self.event_normalizer.normalize(raw_event, source="hook")
```

**Final emitted event structure:**
```json
{
  "event": "claude_event",
  "type": "hook",
  "subtype": "token_usage_updated",
  "timestamp": "2024-02-07T...",
  "session_id": "abc123...",
  "data": {
    "session_id": "abc123...",
    "input_tokens": 123,
    "output_tokens": 456,
    "cache_creation_tokens": 789,
    "cache_read_tokens": 012,
    "total_tokens": 1380,
    "timestamp": "2024-02-07T..."
  }
}
```

---

## Dashboard-Side Event Processing

### File: `agents.svelte.ts:654-666`

**Event filter:**
```typescript
if (event.subtype === 'token_usage_updated' || event.type === 'token_usage_updated') {
    const tokenUsage = extractTokenUsage(event);
    if (tokenUsage && sessionId) {
        tokenUsageMap.set(sessionId, tokenUsage);
        console.log('[AgentsStore] Captured token_usage_updated event:', {
            sessionId: sessionId.slice(0, 12),
            totalTokens: tokenUsage.totalTokens,
            inputTokens: tokenUsage.inputTokens,
            outputTokens: tokenUsage.outputTokens,
            timestamp: new Date(timestamp).toLocaleTimeString()
        });
    }
}
```

### File: `agents.svelte.ts:249-265` (extractTokenUsage)

**Token extraction function:**
```typescript
function extractTokenUsage(event: ClaudeEvent): TokenUsage | null {
    if (typeof event.data !== 'object' || !event.data) return null;
    const data = event.data as Record<string, unknown>;

    const inputTokens = (data.input_tokens as number) || 0;
    const outputTokens = (data.output_tokens as number) || 0;
    const cacheCreationTokens = (data.cache_creation_tokens as number) || 0;
    const cacheReadTokens = (data.cache_read_tokens as number) || 0;

    return {
        inputTokens,
        outputTokens,
        cacheCreationTokens,
        cacheReadTokens,
        totalTokens: inputTokens + outputTokens + cacheCreationTokens + cacheReadTokens
    };
}
```

**Expected event structure:**
```json
{
  "subtype": "token_usage_updated",
  "data": {
    "input_tokens": 123,
    "output_tokens": 456,
    "cache_creation_tokens": 789,
    "cache_read_tokens": 012
  }
}
```

---

## Structure Comparison

### Server Sends:
```
event.data.input_tokens              ✅
event.data.output_tokens             ✅
event.data.cache_creation_tokens     ✅
event.data.cache_read_tokens         ✅
```

### Dashboard Expects:
```
event.data.input_tokens              ✅
event.data.output_tokens             ✅
event.data.cache_creation_tokens     ✅
event.data.cache_read_tokens         ✅
```

### ✅ **Field names MATCH!**

---

## Root Cause Analysis

The field names are correct. The issue must be one of:

### 1. **MOST LIKELY: Stop event doesn't have `usage` field**

**Evidence:**
- Line 880: `if "usage" in event:` - only emits token event if this is true
- If Claude's stop hook doesn't provide `usage`, the token event is never emitted
- Dashboard would receive zero events and show zeros

**Test:**
```bash
# Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true

# Trigger a Claude interaction and check logs
tail -f ~/.claude-mpm/logs/hook_handler.log | grep -i usage
```

### 2. **Session ID mismatch**

**Evidence:**
- Line 656: `const sessionId = getSessionId(event);`
- Line 658: `tokenUsageMap.set(sessionId, tokenUsage);`
- If session IDs don't match, tokens are stored under wrong key

**Test:**
```javascript
// In browser console, check event structure
// Open DevTools → Network → WS → Messages
// Look for token_usage_updated events and check session_id
```

### 3. **Event not reaching browser**

**Evidence:**
- Connection manager uses HTTP POST
- Might fail silently if server not running or port wrong

**Test:**
```bash
# Check if server is running
lsof -i :8765

# Check server logs for incoming events
tail -f <server_log_path> | grep token_usage
```

---

## Recommended Fix Strategy

### Phase 1: Verify Event Emission

Add debug logging to confirm token events are being emitted:

**File: `event_handlers.py:995-1016`**
```python
# Add before emission
if DEBUG:
    _log(f"[DEBUG] Emitting token_usage_updated event:")
    _log(f"  - session_id: {session_id[:12]}...")
    _log(f"  - input_tokens: {token_usage_data['input_tokens']}")
    _log(f"  - output_tokens: {token_usage_data['output_tokens']}")
    _log(f"  - cache_creation_tokens: {token_usage_data['cache_creation_tokens']}")
    _log(f"  - cache_read_tokens: {token_usage_data['cache_read_tokens']}")
    _log(f"  - total_tokens: {token_usage_data['total_tokens']}")

self.hook_handler._emit_socketio_event("", "token_usage_updated", token_usage_data)
```

### Phase 2: Verify Event Reception

The dashboard already has console.log at line 658. Check browser console for:
```
[AgentsStore] Captured token_usage_updated event: { sessionId: '...', totalTokens: 123, ... }
```

If you see this log, events are being received correctly.
If you DON'T see this log, events aren't reaching the browser.

### Phase 3: Fix Based on Findings

**If events aren't being emitted (no server logs):**
- Claude's stop hook might not include `usage` field
- Need to investigate Claude hook event structure
- Possibly need alternative source for token usage data

**If events are emitted but not received (server logs exist, no browser logs):**
- Check Socket.IO connection in browser DevTools
- Verify server is broadcasting on correct namespace
- Check for CORS or network issues

**If events are received but zeros still show (browser logs exist):**
- Session ID mismatch
- Need to verify session ID extraction logic in `getSessionId()`
- Check that agent nodes are using correct session IDs

---

## Next Steps

1. **Enable debug mode:**
   ```bash
   export CLAUDE_MPM_HOOK_DEBUG=true
   ```

2. **Trigger a Claude interaction** (simple prompt that completes quickly)

3. **Check logs:**
   ```bash
   # Server-side
   tail -f ~/.claude-mpm/logs/hook_handler.log | grep -E "(token_usage|usage)"

   # Browser-side
   # Open DevTools Console
   # Look for: [AgentsStore] Captured token_usage_updated event
   ```

4. **Based on results:**
   - No server logs → Claude hook doesn't provide usage data
   - Server logs exist, no browser logs → Connection issue
   - Both logs exist → Session ID or data extraction issue

---

## Testing Checklist

- [ ] Verify stop hook event has `usage` field
- [ ] Verify usage fields have correct names (snake_case)
- [ ] Verify token_usage_updated event is emitted
- [ ] Verify event reaches Socket.IO server
- [ ] Verify event broadcasts to dashboard
- [ ] Verify session ID matches between event and agent
- [ ] Verify extractTokenUsage returns non-null
- [ ] Verify tokenUsageMap.set is called with correct session ID
- [ ] Verify agent node retrieves tokens from tokenUsageMap

---

## Summary

**Field names are correct.** The issue is likely that:
1. Claude's stop hook doesn't include `usage` field (most likely)
2. Session IDs don't match between events and agent nodes
3. Events aren't reaching the browser due to connection issues

**Next action:** Enable debug logging and verify which scenario applies.
