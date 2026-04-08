# Stop Hook "Blocking Error" Analysis

**Date**: 2026-04-05  
**Status**: Research complete — behavior is intentional, terminology is confusing

---

## Summary

The "Stop hook blocking error" message shown by Claude Code is **not a bug**. It is Claude Code's UI label for a Stop hook that returns `{"decision": "block", ...}`. The claude-mpm Stop hook intentionally blocks when there are unread cross-project messages, surfacing them to the user before the session ends.

---

## 1. Hook Configuration — Two Layers

There are **two separate hook configurations** active in this project, which is the primary source of confusion.

### Layer 1: Plugin hooks (from the installed claude-mpm plugin)

Source: `~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4/hooks/hooks.json`

```json
"Stop": [{
  "matcher": "*",
  "hooks": [{
    "type": "command",
    "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/mpm_hook_handler.py Stop",
    "timeout": 60
  }]
}]
```

`${CLAUDE_PLUGIN_ROOT}` is a Claude Code variable that expands to the plugin's install directory: `~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4`. The error message the user sees — `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/mpm_hook_handler.py Stop` — is this command, possibly with the variable still unexpanded in the UI display.

### Layer 2: Project-level hooks (from .claude/settings.local.json)

Source: `/Users/masa/Projects/claude-mpm/.claude/settings.local.json`

```json
"Stop": [{
  "matcher": "*",
  "hooks": [{
    "type": "command",
    "command": "/Users/masa/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh",
    "timeout": 60
  }]
}]
```

This uses a fully-resolved absolute path to the bash script, which then calls `python -m claude_mpm.hooks.claude_hooks.hook_handler`.

Both layers are active simultaneously. The error message references the **plugin layer** (layer 1), not the project settings layer.

---

## 2. What `mpm_hook_handler.py` Does on Stop

The plugin's `mpm_hook_handler.py` (`plugin/hooks/mpm_hook_handler.py`) is a thin wrapper. It:

1. Finds the real `claude-hook` binary or `python -m claude_mpm.hooks.claude_hooks.hook_handler`
2. Passes stdin (the hook event JSON) through to the real handler
3. Relays stdout back to Claude Code

The real work happens in `src/claude_mpm/hooks/claude_hooks/event_handlers.py`, method `handle_stop_fast()`.

---

## 3. What the Stop Hook Does — Step by Step

`handle_stop_fast()` (lines 874–1021 of `event_handlers.py`) does the following in order:

1. **Extracts metadata** (working dir, git branch, timestamp, stop reason)
2. **Auto-pause integration** — checks token usage thresholds, finalizes pause session
3. **Response tracking** — records the stop in the response tracker
4. **Unread message check** — queries `MessageService` for unread cross-project messages
5. **Decision**:
   - If unread messages exist AND `stop_hook_active` is False: returns `{"decision": "block", "reason": "📬 N unread cross-project message(s)..."}`
   - Otherwise: emits a stop event to Socket.IO and returns `None` (continue)

The block decision is returned as a Python dict, then serialized to JSON and printed to stdout by `hook_handler.py`'s `handle()` method (lines 426–434).

---

## 4. What "Blocking Error" Means in Claude Code's Hook System

Claude Code's hook system uses this terminology:

- A hook that exits with code 0 and outputs `{"continue": true}` = **continue** (normal)
- A hook that exits with code 0 and outputs `{"decision": "block", "reason": "..."}` = **blocked** (intentional stop)
- A hook that exits non-zero OR writes to stderr = **error** (unintended failure)

**The "Stop hook blocking error" message is Claude Code's UI label for a blocked stop.** It is not an error in the traditional sense. Claude Code displays it as "blocking error" because the Stop hook returning `{"decision": "block"}` prevents the session from ending — which from Claude Code's perspective is an "error" or "interruption" to the normal flow.

The message `"📬 1 unread cross-project message(s)"` confirms this is the intentional code path: the hook found 1 unread message and is blocking the stop to surface it.

---

## 5. Is `${CLAUDE_PLUGIN_ROOT}` Resolving Correctly?

The variable `${CLAUDE_PLUGIN_ROOT}` is a Claude Code native variable for plugin hooks, not a shell variable. Claude Code substitutes it before executing the command. The installed plugin is at:

```
~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4/
```

And `hooks/mpm_hook_handler.py` exists there:
```
~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4/hooks/mpm_hook_handler.py
```

So the variable is resolving correctly. If it were not resolving, the hook would fail with a file-not-found error rather than a "blocking" result.

---

## 6. Why the Error Message Shows the Literal `${CLAUDE_PLUGIN_ROOT}` String

The user's error message reads:
```
Stop hook blocking error from command: "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/mpm_hook_handler.py Stop"
```

Claude Code shows the **original command string** from `hooks.json` in the error/notification UI, before variable expansion. The variable is expanded at execution time but the display shows the raw command. This is a UX quirk in Claude Code's hook notification display.

---

## 7. Is the "Blocking" Intentional or a Bug?

**It is intentional.** The design intent (documented in code comments at lines 949–951):

> Check for unread cross-project messages. If unread messages exist AND this isn't a re-triggered stop (stop_hook_active), block the stop so Claude sees the unread messages and can act on them.

The hook marks the notified messages as read immediately (lines 991–993) and resets the message check throttle, so on the next UserPromptSubmit the user gets a fresh notification. This prevents infinite blocking loops via `stop_hook_active`.

**However**, there is a UX problem: Claude Code labels this an "error" when it is actually a designed notification. The behavior is correct; the labeling is confusing.

---

## 8. Potential Real Errors

The "blocking error" label could also indicate a genuine failure if:

1. `${CLAUDE_PLUGIN_ROOT}` does not expand (plugin not installed) → file not found → non-zero exit → stderr output
2. The `python3` import of `claude_mpm` fails → the thin wrapper falls back to `{"continue": true}` (safe, not blocking)
3. The real handler raises an unhandled exception → returns `{"continue": true}` due to the `except Exception` catch-all

In the user's case, the presence of `"📬 1 unread cross-project message(s)"` in the notification confirms this is case 1 of the intentional blocking path, not a genuine error.

---

## Files Referenced

- `/Users/masa/Projects/claude-mpm/.claude/settings.local.json` — project-level hook config (uses absolute path to shell script)
- `/Users/masa/Projects/claude-mpm/plugin/hooks/hooks.json` — plugin hook config source (uses `${CLAUDE_PLUGIN_ROOT}`)
- `~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4/hooks/hooks.json` — installed plugin hooks (what Claude Code actually uses)
- `~/.claude/plugins/cache/claude-mpm-marketplace/claude-mpm/5.11.4/hooks/mpm_hook_handler.py` — thin delegating wrapper
- `/Users/masa/Projects/claude-mpm/plugin/hooks/mpm_hook_handler.py` — source for the above
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/hook_handler.py` — real hook handler (ClaudeHookHandler class)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/hooks/claude_hooks/event_handlers.py:874` — `handle_stop_fast()` with block logic at lines 949–1014
