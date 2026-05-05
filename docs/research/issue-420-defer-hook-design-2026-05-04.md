# Issue #420: Native Circuit-Breaker via Claude Code Hook Protocol

**Date**: 2026-05-04
**Status**: Complete
**Issue**: #420
**Classification**: Actionable — design recommendation with implementation sketch

---

## 1. Current Claude Code Hook Protocol Capabilities

### 1.1 PreToolUse Response Shapes

A `PreToolUse` hook can return any of the following response shapes (all via stdout JSON):

**Old continue/block format** (still accepted, works in all versions):
```json
{"continue": true}
{"continue": false}
{"continue": true, "tool_input": {...}}
```

**New `hookSpecificOutput` format** (v2.0.30+ for input modification; v2.1.89+ for `defer`):
```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "allow",
    "updatedInput": { ... }
  }
}
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Reason shown to user"
  }
}
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask"
  }
}
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "defer"
  }
}
```

The four `permissionDecision` values are: `allow`, `deny`, `ask`, `defer`.

**`deny`** — blocks the tool call immediately, shows `permissionDecisionReason` to the user.
Works in both interactive and headless (`-p`) modes.

**`defer`** — exits the headless session with `stop_reason: "tool_deferred"` and writes the
pending tool call to disk for external review. Resume with `claude -p --resume <session-id>`.
**Critically: `defer` is silently ignored in interactive sessions.** It only applies to headless
(`-p`) mode.

**`ask`** — prompts the user for approval. Interactive only.

The non-blocking async response used by the fast hook is a separate mechanism:
```json
{"async": true, "asyncTimeout": 60000}
```
This tells Claude Code the hook runs in the background and does not produce a blocking decision.

### 1.2 PermissionRequest Hook

`PermissionRequest` is a distinct event (separate from `PreToolUse`) that fires when Claude Code's
internal permission policy layer needs an explicit allow/deny. The response format wraps the same
`permissionDecision` field:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PermissionRequest",
    "permissionDecision": "allow | deny",
    "permissionDecisionReason": "..."
  }
}
```

MPM already implements this via `src/claude_mpm/hooks/permission_policy.py` (issue #421).

### 1.3 PreToolUse Payload Fields Available for Decision Logic

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "git push origin main --force" },
  "session_id": "abc123...",
  "cwd": "/working/directory"
}
```

No agent-identity field distinguishes PM from subagent — both appear as the same top-level
`tool_name` invocation from Claude Code's perspective.

---

## 2. MPM's Current Circuit-Breaker Architecture

### 2.1 Existing Hook Infrastructure

Three hook scripts run on `PreToolUse`:

| Matcher | Script | Purpose |
|---------|--------|---------|
| `Agent` | `python3 -m claude_mpm.hooks.model_tier_hook` | Injects model into Agent tool calls |
| `Bash` | `python3 -m claude_mpm.hooks.ztk_hook` | Rewrites Bash commands through ztk for token compression |
| `*` | `claude-hook` | Forwards events to dashboard; returns `{"async": true, "asyncTimeout": 60000}` (non-blocking) |

**Key finding**: The `claude-hook` fast path (`claude-hook-fast.sh`, line 146) always returns
`{"async": true, "asyncTimeout": 60000}` — this is a background observation hook only. It has no
ability to block tool calls. The Python handler (`hook_handler.py`) also always emits
`{"continue": True}` (line 619) for non-Stop events.

### 2.2 No Current Blocking Mechanism

There is currently **no mechanism in MPM to block a tool call based on monitor state**. The
circuit-breaker system referenced in `.claude/settings.json` spinner verbs (`"Checking circuit
breakers"`) exists entirely at the PM instruction/prompt level — it is soft enforcement that can
be ignored by the model.

The `AutoPauseHandler` (`src/claude_mpm/hooks/claude_hooks/auto_pause_handler.py`) detects context
threshold crossings (70%, 85%, 90%, 95%) and records actions during pause mode, but does **not**
emit a blocking `PreToolUse` response. It only logs and notifies.

The `MonitorAgent` (`src/claude_mpm/services/agents/monitor_agent.py`) runs as a background thread
in SDK mode with an `auto_pause_threshold: int = 95`, but communicates via `HookEventBus` — it
emits warnings, it does not block tool calls.

### 2.3 PermissionRequest Hook (Issue #421 — Already Implemented)

`src/claude_mpm/hooks/permission_policy.py` implements real allow/deny decisions for the
`PermissionRequest` event. Current rules:

- Safe tools (Read, Glob, Grep, etc.) → always allow
- Mutating tools (Edit, Write, MultiEdit) from read-only agent tiers → deny
- Destructive Bash patterns (rm -rf /, sudo rm, fork bombs, dd to raw disk) → deny
- Default → allow (fail open)

This is already wired in `.claude/settings.json` under `"PermissionRequest"` with
`python3 -m claude_mpm.hooks.model_tier_hook`.

---

## 3. What a Native Circuit-Breaker Would Look Like

### 3.1 Scenario: MonitorAgent State = CRITICAL (context >= 95%)

The `ContextUsageTracker` stores state in a file-based store keyed by session. The "critical"
threshold is `THRESHOLDS["critical"] = 0.95`. When this is crossed, a circuit-breaker hook would:

1. Read the context usage state file (already exists at `~/.claude-mpm/`)
2. Check if `threshold_reached == "critical"` or `percentage_used >= 0.95`
3. If so, return `deny` with a reason

**Hook response for circuit-break on critical context:**

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "Circuit breaker: context at 95%+. Complete current task and /compact or start a new session."
  }
}
```

### 3.2 What `defer` Would Look Like for Headless Pipelines

For a headless (`-p`) workflow where human review is desired:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "defer"
  }
}
```

Claude Code exits with `stop_reason: "tool_deferred"`, session persists on disk. MPM messaging
could pick up the deferred tool details and send an approval request.

**This is not usable for MPM's primary interactive mode** — `defer` is silently ignored there.

---

## 4. Is `PermissionRequest` vs `PreToolUse` the Right Hook?

**Short answer: Use `PreToolUse` for the context circuit-breaker. Use `PermissionRequest` for
tool-access policy (what issue #421 already implements).**

The semantic distinction:

| Hook | When it fires | Appropriate for |
|------|--------------|-----------------|
| `PermissionRequest` | Claude Code's internal policy layer needs an explicit decision | Tool-access policy: which tools which agents can use |
| `PreToolUse` | Just before a tool executes, every time | Dynamic, state-based blocking: "stop because context is critical" |

A context-level circuit-breaker is state-dependent and dynamic — the same `Edit` call should be
allowed at 50% context and denied at 97%. That is `PreToolUse` territory.

`PermissionRequest` is better suited for structural rules that don't vary with session state (e.g.,
read-only agents cannot call `Write`, which is already in `permission_policy.py`).

The `PermissionRequest` hook **could** technically serve as the circuit-breaker by checking context
state in `permission_policy.evaluate()`, but this would pollute the policy engine with session
state concerns and make it harder to test in isolation.

---

## 5. Recommended Approach

**Use `PreToolUse` deny + context state, implemented as a new dedicated hook script.**

Do NOT use `defer` (only works headless). Do NOT bolt context state into `PermissionRequest`
(wrong abstraction). Do NOT modify the fast bash hook (async, non-blocking by design).

### 5.1 Implementation Sketch

**New file: `src/claude_mpm/hooks/context_circuit_breaker.py`**

```python
#!/usr/bin/env python3
"""PreToolUse circuit-breaker: blocks tool calls when context is critical.

Returns hookSpecificOutput.permissionDecision = "deny" when the session's
context usage tracker reports >= 95% (the "critical" threshold).

Designed to be fast: reads a single JSON file from disk, no network calls,
no Python import chains beyond stdlib + StateStorage.
"""
import json
import sys
from pathlib import Path

_CRITICAL_THRESHOLD = 0.95
_STATE_FILE_GLOB = "~/.claude-mpm/context_usage_*.json"  # adjust to actual path

def _get_context_percentage(session_id: str) -> float | None:
    """Read context percentage from file-based state. Returns None on any error."""
    try:
        from claude_mpm.services.infrastructure.context_usage_tracker import ContextUsageTracker
        tracker = ContextUsageTracker()
        state = tracker.get_current_state()
        return state.percentage_used / 100.0
    except Exception:
        return None

def main() -> None:
    try:
        event = json.load(sys.stdin)
    except Exception:
        print(json.dumps({"continue": True}))
        return

    session_id = event.get("session_id", "")
    pct = _get_context_percentage(session_id)

    if pct is not None and pct >= _CRITICAL_THRESHOLD:
        result = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"Circuit breaker: context at {pct:.0%}. "
                    "Use /compact or start a new session before continuing."
                ),
            }
        }
        print(json.dumps(result))
        return

    print(json.dumps({"continue": True}))

if __name__ == "__main__":
    main()
```

**Registration in `.claude/settings.json`** — add before the `*` catchall in `PreToolUse`:

```json
{
  "matcher": "*",
  "hooks": [
    {
      "type": "command",
      "command": "python3 -m claude_mpm.hooks.context_circuit_breaker",
      "timeout": 3
    }
  ]
}
```

Hook order matters: this new hook runs before `claude-hook` (the async dashboard forwarder), so a
`deny` response stops execution before the async hook fires.

**Files that change:**

| File | Change |
|------|--------|
| `src/claude_mpm/hooks/context_circuit_breaker.py` | New file (circuit-breaker hook) |
| `.claude/settings.json` | Add hook entry to `PreToolUse` array before the `*`/`claude-hook` entry |
| `tests/hooks/test_context_circuit_breaker.py` | New test file |

### 5.2 Alternative: Extend `PermissionRequest` (Not Recommended)

Adding context-state logic to `permission_policy.evaluate()` in
`src/claude_mpm/hooks/permission_policy.py` (line 114) would work mechanically but mixes
structural policy (who can use what tool) with session state (how full is the context window).
Avoid this path.

---

## 6. Risk and Complexity Assessment

**Overall: SMALL (S)**

| Dimension | Assessment |
|-----------|-----------|
| Implementation complexity | S — ~50 lines of Python, reads existing state file |
| Integration risk | S — hook runs independently; deny is a standard protocol response |
| Test complexity | S — unit-testable with mocked `ContextUsageTracker.get_current_state()` |
| Operational risk | M — false triggers if state file has stale data from a previous session |
| Interactive mode gap | None — `deny` works in interactive mode (unlike `defer`) |
| Headless mode | `deny` also works; `defer` would be addable later if needed |

**Primary operational risk**: The `ContextUsageTracker` state file persists between sessions. A
stale "critical" state from a prior session could incorrectly block the next session's first tool
call. Mitigation: check `session_id` in the state file against the incoming `session_id` before
blocking; reset state on `SessionStart` hook.

**`defer` complexity**: M-to-L if pursued. Requires MPM messaging integration to handle
`stop_reason: "tool_deferred"` output, approve/deny the deferred tool, and `claude -p --resume`.
Only useful for future headless/CI workflows; zero value for current interactive mode.

---

## 7. What NOT to Do

- **Do not use `defer` for interactive circuit-breaking** — it is silently ignored.
- **Do not add context state to `PermissionRequest`** — wrong semantic layer.
- **Do not modify `claude-hook-fast.sh`** — it is explicitly async/non-blocking by design; any
  blocking decision there would add latency to every single tool call.
- **Do not replace instruction-level circuit breakers (#1-#8) with hook-level enforcement** —
  hooks cannot distinguish PM-direct vs subagent tool calls.

---

## Sources

- `src/claude_mpm/scripts/claude-hook-fast.sh` — fast hook (line 146: always async)
- `src/claude_mpm/hooks/claude_hooks/hook_handler.py` — Python handler (line 619: always continue)
- `src/claude_mpm/hooks/model_tier_hook.py` — PermissionRequest handler (lines 100-115)
- `src/claude_mpm/hooks/permission_policy.py` — policy engine (lines 59-177)
- `src/claude_mpm/hooks/ztk_hook.py` — Bash rewriter using hookSpecificOutput.updatedInput format
- `src/claude_mpm/hooks/claude_hooks/auto_pause_handler.py` — threshold detection (lines 62-67)
- `src/claude_mpm/services/agents/monitor_agent.py` — MonitorAgent (auto_pause_threshold: 95)
- `src/claude_mpm/services/infrastructure/context_usage_tracker.py` — THRESHOLDS dict
- `.claude/settings.json` — hook registration (lines 3-106)
- `docs/research/defer-hook-evaluation-2026-04-02.md` — prior defer evaluation (confirmed: defer
  only works headless; deny is the correct mechanism for interactive circuit-breaking)
- `docs/developer/pretool-use-hooks.md` — hook response format documentation
