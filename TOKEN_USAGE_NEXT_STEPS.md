# Token Usage Investigation - Next Steps

**Date**: 2026-02-07
**Status**: Root cause identified, verification pending

---

## TL;DR

**Problem**: Dashboard shows zeros for token usage.

**Root Cause**: Claude Code stop hooks don't include `usage` field.

**Next Step**: Verify if AssistantResponse hooks contain usage data.

**Time Required**: 5 minutes

---

## Quick Verification (Do This First)

Run this command to check if AssistantResponse contains usage data:

```bash
# 1. Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true

# 2. Trigger a Claude interaction
echo "What is 2+2?" | claude

# 3. Run verification script
python3 verify_assistant_response_usage.py
```

**Expected outcomes**:
- ✅ **Usage field found** → We can fix token tracking immediately
- ❌ **No usage field** → Need alternative source (see Option B below)

---

## Option A: If AssistantResponse Has Usage (Best Case)

**Implementation** (15-30 minutes):

1. **Update event_handlers.py** to extract usage from AssistantResponse:

```python
def handle_assistant_response(self, event):
    # Add after line 1192 (existing code)
    session_id = event.get("session_id", "")

    # NEW: Extract token usage if available
    if "usage" in event:
        usage_data = event["usage"]
        token_usage_data = {
            "session_id": session_id,
            "input_tokens": usage_data.get("input_tokens", 0),
            "output_tokens": usage_data.get("output_tokens", 0),
            "cache_creation_tokens": usage_data.get("cache_creation_input_tokens", 0),
            "cache_read_tokens": usage_data.get("cache_read_input_tokens", 0),
            "total_tokens": (...),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.hook_handler._emit_socketio_event("", "token_usage_updated", token_usage_data)
```

2. **Test the fix**:
   - Restart monitoring server
   - Trigger Claude interaction
   - Check dashboard TokensView

3. **Verify success**:
   - Browser console: Look for `[AgentsStore] Captured token_usage_updated event`
   - Dashboard: Check if token counts are non-zero

---

## Option B: If No Usage in Any Hook (Fallback)

Need to explore alternative sources:

### B1. Check Claude Code Session Files

```bash
# Search for token usage in Claude's session data
find ~/.claude -name "*.json" -o -name "*.jsonl" | xargs grep -l "usage\|token" | head -10
```

If found, implement session file parser to extract usage.

### B2. Parse CLI Output

```bash
# Check if Claude CLI displays token usage
echo "test" | claude 2>&1 | grep -i token
```

If found, implement CLI output parser.

### B3. Request Claude Code Enhancement

File feature request with Anthropic:
- Request `usage` field in stop hooks
- OR expose token usage through alternative API
- Reference: Other tools need this data for monitoring

### B4. Direct Anthropic API Integration

**Last resort** (complex, fragile):
- Intercept Claude Code's API calls
- Extract usage from responses before they reach Claude Code
- Requires reverse engineering Claude Code internals

---

## File Locations

### Investigation Reports
- **Main report**: `docs/research/token-usage-source-investigation-2026-02-07.md`
- **Previous diagnostics**: `TOKEN_EMISSION_DIAGNOSTIC.md`, `DIAGNOSTIC_REPORT.md`

### Code to Modify (if Option A works)
- **Event handlers**: `src/claude_mpm/hooks/claude_hooks/event_handlers.py`
  - Method: `handle_assistant_response()` (lines 1160-1256)
  - Add token extraction after line 1192

### Verification Script
- **Script**: `verify_assistant_response_usage.py`
- **Usage**: `python3 verify_assistant_response_usage.py`

---

## Success Criteria

Token tracking is working when:
1. ✅ Browser console shows: `[AgentsStore] Captured token_usage_updated event`
2. ✅ Dashboard TokensView displays non-zero counts
3. ✅ Cache efficiency percentage shows correctly
4. ✅ Per-agent token breakdowns appear

---

## Timeline

| Scenario | Time to Fix |
|----------|-------------|
| **AssistantResponse has usage** | 30 minutes (implement + test) |
| **Need session file parsing** | 2-4 hours (discover + implement) |
| **Need CLI parsing** | 3-5 hours (parse logic + reliability) |
| **Need Claude Code enhancement** | Unknown (depends on Anthropic) |

---

## Decision Tree

```
START
  |
  ├─> Run verification script
  |
  ├─> AssistantResponse has usage?
  |   ├─> YES → Implement Option A (30 min)
  |   └─> NO  → Continue
  |
  ├─> Check session files for usage?
  |   ├─> YES → Implement parser (2-4 hours)
  |   └─> NO  → Continue
  |
  ├─> CLI displays token usage?
  |   ├─> YES → Implement CLI parser (3-5 hours)
  |   └─> NO  → Continue
  |
  └─> Request Claude Code enhancement
      (timeline unknown)
```

---

## Contact

**Questions**: Check detailed investigation report
**Report**: docs/research/token-usage-source-investigation-2026-02-07.md
**Status**: Awaiting verification results

---

**Next Action**: Run `python3 verify_assistant_response_usage.py`
