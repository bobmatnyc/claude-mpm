# SessionStart Hook Matcher Issue - Visual Explanation

## The Problem: Event Flow Breakdown

```
┌─────────────────────────────────────────────────────────────────┐
│                      Claude Code Startup                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                    Trigger: SessionStart:startup
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Claude Code Hook Matching Logic                    │
│                                                                  │
│  1. Event Type:  SessionStart                                   │
│  2. Query/Matcher: "startup"                                    │
│  3. Search settings.json for:                                   │
│     - settings.hooks.SessionStart                               │
│     - Find matchers that match "startup"                        │
└───────────────────────────────┬─────────────────────────────────┘
                                │
                                ▼
                         Check Configuration
                                │
                ┌───────────────┴────────────────┐
                │                                │
                ▼                                ▼
     ❌ CURRENT (BROKEN)              ✅ FIXED (WORKING)
                │                                │
                ▼                                ▼
┌──────────────────────────┐    ┌──────────────────────────────┐
│ Current settings.json:   │    │ Fixed settings.json:         │
│                          │    │                              │
│ "SessionStart": [        │    │ "SessionStart": [            │
│   {                      │    │   {                          │
│     "hooks": [...]       │    │     "matcher": "*",    ← NEW │
│   }                      │    │     "hooks": [...]           │
│ ]                        │    │   }                          │
│                          │    │ ]                            │
│ ❌ No matcher field      │    │ ✅ Matcher present           │
└────────────┬─────────────┘    └──────────────┬───────────────┘
             │                                  │
             ▼                                  ▼
  Claude Code Matcher Logic:       Claude Code Matcher Logic:
  1. Look for "matcher" field      1. Look for "matcher" field
  2. ❌ NOT FOUND                   2. ✅ FOUND: "*"
  3. Return 0 hooks                3. Match "startup" against "*"
                                   4. ✅ MATCHES
             │                     5. Return 1 hook
             ▼                                  │
                                                ▼
     ⚠️ ERROR MESSAGE                    🎉 SUCCESS
  "SessionStart:startup               Hook executes successfully
   hook error"                        No error message
```

## Event Type Comparison: Matcher vs No-Matcher

### Tool Events (Need Matchers) ✅ Working

```
Event: PreToolUse (tool="Bash")
      │
      ▼
Claude Code: "Find hooks for PreToolUse with matcher 'Bash'"
      │
      ▼
Configuration:
{
  "PreToolUse": [
    {
      "matcher": "*",      ← Matches "Bash", "Read", any tool
      "hooks": [...]
    }
  ]
}
      │
      ▼
✅ Result: Hook executes for Bash tool
```

### Simple Events (No Matchers Needed) ✅ Working

```
Event: UserPromptSubmit
      │
      ▼
Claude Code: "Find hooks for UserPromptSubmit with no matcher"
      │
      ▼
Configuration:
{
  "UserPromptSubmit": [
    {
      "hooks": [...]       ← No matcher needed
    }
  ]
}
      │
      ▼
✅ Result: Hook executes for all prompts
```

### SessionStart (Needs Matcher BUT Missing) ❌ Broken

```
Event: SessionStart:startup
      │
      ▼
Claude Code: "Find hooks for SessionStart with matcher 'startup'"
      │
      ▼
Configuration (CURRENT):
{
  "SessionStart": [
    {
      "hooks": [...]       ← ❌ No matcher field
    }
  ]
}
      │
      ▼
❌ Result: 0 hooks found → Error message
```

### SessionStart (With Matcher) ✅ Fixed

```
Event: SessionStart:startup
      │
      ▼
Claude Code: "Find hooks for SessionStart with matcher 'startup'"
      │
      ▼
Configuration (FIXED):
{
  "SessionStart": [
    {
      "matcher": "*",      ← ✅ Matches "startup", "resume", etc.
      "hooks": [...]
    }
  ]
}
      │
      ▼
✅ Result: Hook executes successfully
```

## Code Change Required

### Location: `src/claude_mpm/hooks/claude_hooks/installer.py` line 524-531

#### BEFORE (Current - Broken)
```python
# Non-tool events don't need a matcher - just hooks array
non_tool_events = ["UserPromptSubmit", "Stop", "SubagentStop",
                   "SubagentStart", "SessionStart"]  # ← SessionStart here
for event_type in non_tool_events:
    settings["hooks"][event_type] = [
        {
            "hooks": [hook_command],  # ❌ No matcher
        }
    ]
```

#### AFTER (Fixed - Working)
```python
# Simple events (no matcher needed)
simple_events = ["UserPromptSubmit", "Stop", "SubagentStop", "SubagentStart"]
for event_type in simple_events:
    settings["hooks"][event_type] = [
        {
            "hooks": [hook_command],
        }
    ]

# SessionStart needs matcher for subtypes (startup, resume)
settings["hooks"]["SessionStart"] = [
    {
        "matcher": "*",  # ✅ Match all subtypes
        "hooks": [hook_command],
    }
]
```

## SessionStart Event Subtypes

```
SessionStart Event Family
│
├─ SessionStart:startup
│  └─ Fired when Claude Code starts up
│
├─ SessionStart:resume
│  └─ Fired when resuming existing session
│
└─ SessionStart:* (future subtypes)
   └─ Matched by "matcher": "*"
```

## Matcher Pattern Matching Logic

```
Matcher Value     |  Matches Query      |  Example
─────────────────────────────────────────────────────────
"*"              |  ALL queries        |  "startup", "resume", "new"
"startup"        |  Only "startup"     |  "startup" ✅, "resume" ❌
"resume"         |  Only "resume"      |  "resume" ✅, "startup" ❌
(no matcher)     |  Undefined queries  |  Works ONLY if query=undefined
```

## Debug Log Evidence

### Broken (Current Configuration)
```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 0 hook matchers in settings        ← ❌ Problem here
[DEBUG] Matched 0 unique hooks for query "startup"
[DEBUG] Found 0 hook commands to execute         ← Results in error
```

### Fixed (With Matcher)
```
[DEBUG] Executing hooks for SessionStart:startup
[DEBUG] Getting matching hook commands for SessionStart with query: startup
[DEBUG] Found 1 hook matcher in settings         ← ✅ Found matcher
[DEBUG] Matcher "*" matches query "startup"      ← ✅ Pattern matches
[DEBUG] Matched 1 unique hook for query "startup"
[DEBUG] Found 1 hook command to execute          ← ✅ Hook executes
[DEBUG] Executing: /path/to/claude-hook-handler.sh
```

## Testing Workflow

```
1. Apply Fix
   └─ Edit installer.py: Add SessionStart with matcher: "*"

2. Reinstall Hooks
   └─ Run: claude-mpm install-hooks --force

3. Verify Configuration
   └─ Check: cat ~/.claude/settings.json | jq '.hooks.SessionStart'
   └─ Expected: [{"matcher": "*", "hooks": [...]}]

4. Test Startup Event
   └─ Restart Claude Code
   └─ Check: ✅ No "SessionStart:startup hook error"

5. Test Resume Event
   └─ Start conversation → Close → Reopen
   └─ Check: ✅ No "SessionStart:resume hook error"

6. Monitor Logs
   └─ tail -f /tmp/claude-mpm-hook.log
   └─ Expected: "Processing SessionStart" messages
```

## Event Configuration Decision Tree

```
                      New Hook Event
                            │
                            ▼
              Does event have subtypes/variants?
                   /              \
                  /                \
                YES                 NO
                 │                  │
                 ▼                  ▼
        Use Matcher Pattern    Use Simple Pattern
                 │                  │
                 ▼                  ▼
        ┌──────────────────┐  ┌──────────────────┐
        │ "EventName": [   │  │ "EventName": [   │
        │   {              │  │   {              │
        │     "matcher":"*"│  │     "hooks": [...│
        │     "hooks": [...│  │   }              │
        │   }              │  │ ]                │
        │ ]                │  └──────────────────┘
        └──────────────────┘
                 │
                 ▼
          Examples:
          • PreToolUse (subtypes: tool names)
          • PostToolUse (subtypes: tool names)
          • SessionStart (subtypes: startup, resume)
```

## Summary

**Problem**: SessionStart configured as simple event but Claude Code treats it as matcher-based event

**Why it fails**: Claude Code looks for matcher pattern to match "startup" or "resume" query, finds none

**Fix**: Add `"matcher": "*"` to SessionStart configuration

**Result**: Hooks match all SessionStart subtypes (startup, resume, future subtypes)

**Impact**: Eliminates user-visible error messages on every startup and session resume
