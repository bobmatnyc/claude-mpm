# Context Circuit Breaker

**Module**: `src/claude_mpm/hooks/context_circuit_breaker.py`  
**Hook event**: `PreToolUse`  
**Spec**: `SPEC-HOOKS-11~1` (see `docs/specs/hooks.md`)

## What it does

Reads cumulative context-usage state from the per-session state file
(`.claude-mpm/state/context-usage.json`) and emits a *warning annotation*
when the session's context exceeds a configurable threshold.  Read-only and
recovery tools are always allowed through so a session that has hit the
threshold can still self-recover via `/compact`, `Read`, `Grep`, or
`/mpm-resume`.

The breaker is **allow-with-warning only** — it never emits
`permissionDecision: "deny"`.  That was the pre-#642 behavior and made
sessions unrecoverable.

## Configuration knobs

### Disable the breaker entirely

| Method | Value |
|--------|-------|
| Environment variable | `CLAUDE_MPM_DISABLE_CONTEXT_BREAKER=1` (or `true` / `yes` / `on`) |
| `.claude/settings.json` | `{"context_circuit_breaker": {"disabled": true}}` |
| `.claude/settings.local.json` | same key |
| `~/.claude/settings.json` | same key |

Precedence: env var > `settings.local.json` > `settings.json` > `~/.claude/settings.json`.

### Override the warning threshold (issue #681)

The default threshold is **95 %**.  To raise or lower it:

| Method | Example |
|--------|---------|
| Environment variable | `CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD=85` |
| `.claude/settings.json` | `{"context_circuit_breaker": {"threshold_pct": 85}}` |
| `.claude/settings.local.json` | same key |
| `~/.claude/settings.json` | same key |

Precedence: env var > `settings.local.json` > `settings.json` > `~/.claude/settings.json` > default (95.0).

**Validation**: values must be numeric and in the range `[1, 100]` (inclusive).
Values outside this range or non-numeric strings are silently ignored and the
default 95.0 is used (fail-open policy — bad config must never hard-block a
session).

### Both knobs together

```json
{
  "context_circuit_breaker": {
    "disabled": false,
    "threshold_pct": 85
  }
}
```

If `disabled: true` is set, the threshold knob is irrelevant — the breaker is
bypassed entirely regardless of the threshold value.

## How it works

1. **Tool allow-list check** — tools in `ALWAYS_ALLOWED_TOOLS` (`Read`, `Grep`,
   `Glob`, `LS`, `NotebookRead`, `WebSearch`, `WebFetch`, `TodoRead`,
   `TodoWrite`, `exit_plan_mode`, and MPM recovery skills) pass through
   unconditionally even when the threshold is exceeded.

2. **Disable-switch check** — returns pass-through if the breaker is disabled.

3. **State file load** — reads
   `.claude-mpm/state/context-usage.json` (written by `ContextUsageTracker`).
   Missing, unreadable, or malformed files → fail-open (pass-through).

4. **Session-ID guard** — stale state from a previous session (mismatched
   `session_id`) → fail-open.

5. **Percentage computation** — prefers recomputing from raw token counts
   (`cumulative_input_tokens + cumulative_output_tokens`) against the real
   model context window (resolved via `model_context_window.resolve_context_window()`).
   Falls back to the stored `percentage_used` field, clamped to `[0, 100]`.
   This prevents false positives on 1 M-context models that have an old
   percentage written against a 200 K budget.

6. **Threshold comparison** — resolves the effective threshold via
   `_resolve_threshold(cwd)` (env > settings > default).  If
   `percentage < threshold` → pass-through.

7. **Warning emission** — returns
   `{"permissionDecision": "allow", "permissionDecisionReason": "<text>"}`.
   The reason text includes:
   - current percentage
   - instructions to `/compact` or use `/mpm-resume`
   - how to disable (`CLAUDE_MPM_DISABLE_CONTEXT_BREAKER`)
   - how to adjust the threshold (`CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD` /
     `threshold_pct`)

## Fail-open policy

At every decision point — missing state file, malformed JSON, invalid config
value, unexpected exception — the breaker returns an empty dict (pass-through).
A false positive (blocking an active session) is far more harmful than a missed
warning.

## Related issues and references

- `#642` — original fix: dynamic context window, allow-with-warning, always-allowed tools
- `#681` — configurable threshold (`threshold_pct` / `CLAUDE_MPM_CONTEXT_BREAKER_THRESHOLD`)
- `SPEC-HOOKS-11~1` in `docs/specs/hooks.md`
- State writer: `src/claude_mpm/services/infrastructure/context_usage_tracker.py`
- Model window map: `src/claude_mpm/hooks/model_context_window.py`
