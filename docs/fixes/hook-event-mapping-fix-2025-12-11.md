# Hook Event Naming Fix - Summary

## Problem
Events were displaying as `[hook] unknown.claude_event` instead of meaningful names like `[hook] user_prompt_submit` in the Claude MPM monitor dashboard.

## Root Cause
The subtype mapping logic in `src/claude_mpm/services/socketio/server/core.py` had two issues:

1. **Old string manipulation** (lines 306-309): Used brittle `.replace("submit", "").replace("use", "_use")` logic
2. **Limited mapping** (lines 316-327): Only 6 event types mapped, others fell back to `"unknown"`

The old logic created subtypes like `"userprompt"` (instead of `"user_prompt_submit"`) and failed for most event types.

## Solution

### 1. Comprehensive Event Type Mapping
Added complete mapping of all 19 known Claude Code hook event types:

**User Interaction Events:**
- `UserPromptSubmit` → `user_prompt_submit`
- `UserPromptCancel` → `user_prompt_cancel`

**Tool Execution Events:**
- `PreToolUse` → `pre_tool_use`
- `PostToolUse` → `post_tool_use`
- `ToolStart` → `tool_start`
- `ToolUse` → `tool_use`

**Assistant Events:**
- `AssistantResponse` → `assistant_response`

**Session Lifecycle Events:**
- `Start` → `start`
- `Stop` → `stop`
- `SessionStart` → `session_start`

**Subagent Events:**
- `SubagentStart` → `subagent_start`
- `SubagentStop` → `subagent_stop`
- `SubagentEvent` → `subagent_event`

**Task Events:**
- `Task` → `task`
- `TaskStart` → `task_start`
- `TaskComplete` → `task_complete`

**File Operation Events:**
- `FileWrite` → `file_write`
- `Write` → `write`

**System Events:**
- `Notification` → `notification`

### 2. Intelligent Fallback Mechanism
Instead of mapping unknown events to `"unknown"`, implemented automatic PascalCase to snake_case conversion:

```python
def to_snake_case(name: str) -> str:
    """Convert PascalCase event names to snake_case.

    Examples:
        UserPromptSubmit → user_prompt_submit
        PreToolUse → pre_tool_use
        TaskComplete → task_complete
        NewFeatureEvent → new_feature_event (future events)
    """
    import re
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
```

### 3. Debug Logging for Discovery
Added debug logging for unmapped events to help discover new event types as Claude Code evolves:

```python
if hook_event_name not in subtype_map and hook_event_name != "unknown":
    self.logger.debug(
        f"Unmapped hook event: {hook_event_name} → {raw_event['subtype']}"
    )
```

## Testing

### Syntax Verification
✅ Python syntax check passed

### Conversion Function Tests
Verified all 19 known event types map correctly:
- ✅ All mapped events produce correct snake_case subtypes
- ✅ Unknown events automatically convert to snake_case (no "unknown" fallback)
- ✅ No syntax errors or regressions

### Test Results
```
Known event types: 19
All events mapped to snake_case subtypes: ✅
Fallback mechanism tested: ✅
No 'unknown' subtypes (except explicit): ✅
```

## Expected Behavior

### Before Fix
```
[hook] unknown.claude_event
[hook] unknown.claude_event
[hook] user_prompt.claude_event  (only 6 events mapped)
```

### After Fix
```
[hook] user_prompt_submit.claude_event
[hook] pre_tool_use.claude_event
[hook] post_tool_use.claude_event
[hook] assistant_response.claude_event
[hook] notification.claude_event
[hook] new_feature_event.claude_event  (future events auto-convert)
```

## Files Modified
- `src/claude_mpm/services/socketio/server/core.py` (lines 294-368)
  - Removed brittle string manipulation logic
  - Added comprehensive event type mapping (19 event types)
  - Implemented intelligent PascalCase → snake_case fallback
  - Added debug logging for discovery of new event types

## Benefits
1. **Meaningful Event Names**: Events display with descriptive subtypes instead of "unknown"
2. **Future-Proof**: Automatic fallback handles new Claude Code event types without code changes
3. **Debuggability**: Debug logging helps discover new event types as they're introduced
4. **Maintainability**: Comprehensive mapping serves as documentation of all supported events

## Migration
No migration needed - changes are backward compatible. Existing event handling continues to work, but with better naming.
