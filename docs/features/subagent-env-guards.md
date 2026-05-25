# Sub-Agent Environment Guards

**Added in**: v6.4.9

## Overview

Claude MPM injects environment variables into PM and sub-agent processes so that hook scripts can identify which kind of Claude process is running and skip work that is not applicable.

## Environment Variables

### `CLAUDE_MPM_IS_PM=1`

Set in the PM subprocess environment. Indicates that the running Claude Code process is the top-level Project Manager orchestrated by MPM.

Use this to enable PM-only behavior in scripts that are sourced in both PM and standalone contexts.

### `CLAUDE_MPM_SUB_AGENT=1`

Injected by `model_tier_hook.py` into every sub-agent process before it starts. Indicates that the current Claude Code process is a delegated sub-agent, not the PM.

This variable is the primary mechanism for guarding hook scripts against double-execution.

## Guarding Hook Scripts

Hook scripts that are registered globally (for example in `~/.claude/settings.json`) run in every Claude Code process — including PM, sub-agents, and standalone sessions. Use `CLAUDE_MPM_SUB_AGENT` to exit early when the hook is not relevant to sub-agent processes:

```bash
#!/usr/bin/env bash
# Skip processing when running inside an MPM sub-agent
[[ -n "$CLAUDE_MPM_SUB_AGENT" ]] && exit 0

# ... rest of hook logic for PM / standalone contexts only
```

Similarly, to restrict a hook to the PM process only:

```bash
#!/usr/bin/env bash
# Only run when this process is the MPM PM
[[ -z "$CLAUDE_MPM_IS_PM" ]] && exit 0

# ... PM-only hook logic
```

## Why This Matters

Without these guards, a hook registered for PM use (e.g., memory enrichment, session logging) would also fire inside every sub-agent Claude spawns. This causes:

- Duplicate writes to memory/log backends
- Extra latency on every sub-agent tool call
- Confusing entries in session logs attributed to the wrong process

The guard pattern is a one-line fix that eliminates all of these issues.

## Implementation Notes

- `CLAUDE_MPM_IS_PM=1` is set in `src/claude_mpm/` when constructing the PM subprocess command environment.
- `CLAUDE_MPM_SUB_AGENT=1` is injected by `src/claude_mpm/hooks/model_tier_hook.py` as part of the `PreToolUse` hook that configures sub-agent model selection.
- Both variables are unset in unmanaged Claude Code sessions (i.e., when Claude is launched directly without `claude-mpm run`).
