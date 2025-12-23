# MPM Event Schema - Before vs After

## Quick Reference

### Hook Execution Events

| Field | Before (❌ Incorrect) | After (✅ Correct) |
|-------|---------------------|------------------|
| `event` | `"claude_event"` | `"mpm_event"` |
| `source` | `"mpm_hook"` | `"mpm_hook"` |
| `type` | `"hook"` | `"UserPromptSubmit"` (actual hook name) |
| `subtype` | `"execution"` | `"execution"` |

### Example: UserPromptSubmit Hook

#### Before (❌)
```json
{
  "event": "claude_event",
  "source": "mpm_hook",
  "type": "hook",
  "subtype": "execution",
  "data": {
    "hook_type": "UserPromptSubmit",
    "hook_name": "UserPromptSubmit",
    ...
  }
}
```

#### After (✅)
```json
{
  "event": "mpm_event",
  "source": "mpm_hook",
  "type": "UserPromptSubmit",
  "subtype": "execution",
  "data": {
    "hook_type": "UserPromptSubmit",
    "hook_name": "UserPromptSubmit",
    ...
  }
}
```

## All Hook Types

The `type` field now correctly reflects the actual hook:

- `"UserPromptSubmit"` - User submitted a prompt
- `"PreToolUse"` - Before a tool is executed
- `"PostToolUse"` - After a tool is executed
- `"SubagentStart"` - Subagent session started
- `"SubagentStop"` - Subagent session stopped
- `"SessionStart"` - New Claude session started
- `"Stop"` - Claude session stopped
- `"Notification"` - Notification event
- `"AssistantResponse"` - Assistant generated a response

## Frontend Migration

### Old Code (needs update)
```javascript
socket.on("claude_event", (data) => {
  if (data.type === "hook" && data.subtype === "execution") {
    // Hook execution event
    const hookType = data.data.hook_type; // Had to dig into data
  }
});
```

### New Code (correct)
```javascript
socket.on("mpm_event", (data) => {
  if (data.subtype === "execution") {
    // Hook execution event
    const hookType = data.type; // Direct access to hook type
  }
});
```

## Benefits

1. **Clearer Event Names**: "mpm_event" vs "claude_event" distinguishes source
2. **Direct Type Access**: `data.type` contains hook name directly
3. **Easier Filtering**: Filter by `type: "PreToolUse"` instead of checking data
4. **Better Schema**: Follows standard event schema patterns
5. **Type Safety**: Frontend can type-check based on `type` field
