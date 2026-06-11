---
version: "1.1.0"
effort: medium
---

# PM Session Management

**Type**: Framework
**Applies To**: Project Manager Agent
**Load Priority**: On-demand (context limit or session resume)

> **Umbrella skill.** This skill covers the *concepts* of PM session lifecycle:
> the auto-pause threshold system, git-based continuity, and how session
> management fits the PM workflow. The concrete, user-invocable **procedures**
> live in two dedicated skills — use them for the actual steps:
> - **`mpm-session-pause`** — pause and persist current work state.
> - **`mpm-session-resume`** — load context from a paused session.
>
> Do not duplicate their step-by-step instructions here; this skill points at
> them.

## Purpose

This skill provides the conceptual model for PM session pause/resume when
context limits are approaching or when resuming from a previous session. These
protocols are only needed when hitting token limits or starting a session with
existing pause state. For the operational steps, invoke `mpm-session-pause` /
`mpm-session-resume`.

## When This Skill Is Loaded

- Context usage reaches 70%+ thresholds
- Session starts with `.claude-mpm/sessions/ACTIVE-PAUSE.jsonl`
- Session starts with `.claude-mpm/sessions/LATEST-SESSION.txt`
- User runs `/mpm-session-resume`

## Auto-Pause System

The MPM framework automatically tracks context usage and pauses sessions when approaching limits:

### Threshold Levels

| Level | Usage | Behavior |
|-------|-------|----------|
| Caution | 70% | Warning displayed |
| Warning | 85% | Stronger warning |
| **Auto-Pause** | **90%** | **Session pause activated, actions recorded** |
| Critical | 95% | Session nearly exhausted |

### Auto-Pause Behavior (at 90%)

When context usage reaches 90%:

1. Creates `.claude-mpm/sessions/ACTIVE-PAUSE.jsonl`
2. Records all subsequent actions (tool calls, responses) incrementally
3. Displays warning to user about context limits
4. On session end, finalizes to full session snapshot

The incremental recording ensures all work is captured even if the session hits hard limits.

## Session Resume Protocol

> **Procedure moved.** The step-by-step resume flow (detecting
> `ACTIVE-PAUSE.jsonl` vs. `LATEST-SESSION.txt`, the continue/finalize/discard
> prompt, and loading the snapshot) now lives in **`mpm-session-resume`**.
> Invoke that skill rather than duplicating its steps.

At session start the PM checks for two states, both handled by
`mpm-session-resume`:

1. **Active incremental pause** — `.claude-mpm/sessions/ACTIVE-PAUSE.jsonl`
   (auto-pause was triggered; continue, finalize, or discard).
2. **Finalized pause** — `.claude-mpm/sessions/LATEST-SESSION.txt`
   (a clean snapshot exists; load accomplishments + next steps).

## PM Response to Context Warnings

When PM sees context warnings (70%+), follow this protocol:

### Immediate Actions

1. **Wrap up current work phase**
   - Complete the current delegation cycle
   - Don't start new major tasks

2. **Document all in-progress tasks**
   - Ensure all todos are updated with current status
   - Mark BLOCKED todos with specific blockers
   - Add context to in_progress todos

3. **Delegate remaining work with clear handoff**
   - Provide detailed context to agents
   - Include acceptance criteria
   - Reference relevant files and commits

4. **Create summary**
   - What was completed
   - What remains to be done
   - Any blockers or important context

### Example Wrap-Up Sequence

```
Context at 85% - wrapping up current phase

Completed:
- ✅ OAuth2 implementation (commit abc123)
- ✅ Staging deployment verified

In Progress:
- 🔄 QA verification (api-qa testing login flow)

Remaining:
- Documentation update (auth flow docs)
- Production deployment

Creating session snapshot for clean resume...
```

## Git-Based Session Continuity

Git history provides additional session context that complements session snapshots:

### Useful Git Commands

```bash
# Recent commits (what was delivered)
git log --oneline -10

# Uncommitted changes (work in progress)
git status

# Recent work (last 24 hours)
git log --since="24 hours ago" --pretty=format:"%h %s"

# Files changed recently
git log --name-status --since="24 hours ago"
```

### Integration with Session Resume

When resuming a session, PM should:

1. Load session snapshot (if available)
2. Check git log for additional context
3. Verify git status for uncommitted work
4. Reconcile session state with git state

**Example**:
```
Resuming session...

Session snapshot: Work on OAuth2 authentication
Git log: Last commit "feat: add OAuth2 provider" (2 hours ago)
Git status: Uncommitted changes in src/auth/middleware.js

Context: Implementation complete, middleware updates in progress
```

## Session Files Structure

```
.claude-mpm/sessions/
├── ACTIVE-PAUSE.jsonl      # Incremental actions during auto-pause
├── LATEST-SESSION.txt      # Pointer to most recent finalized session
├── session-*.json          # Machine-readable session snapshots
├── session-*.yaml          # YAML format
└── session-*.md            # Human-readable markdown
```

### File Purposes

- **ACTIVE-PAUSE.jsonl**: Real-time action recording during auto-pause
- **LATEST-SESSION.txt**: Points to most recent finalized session file
- **session-*.json**: Complete session state (todos, context, agents used)
- **session-*.yaml**: Same as JSON but YAML format
- **session-*.md**: Human-readable summary for quick review

## Best Practices

### When Context Limits Approach

1. **Don't panic**: Auto-pause system will capture your work
2. **Finish current phase**: Complete the delegation in progress
3. **Update todos**: Ensure all todos reflect current state
4. **Create handoff context**: Next PM session needs to understand state

### When Resuming Sessions

1. **Review session snapshot**: Understand what was accomplished
2. **Check git history**: Verify actual state matches snapshot
3. **Validate uncommitted work**: Any WIP that wasn't tracked?
4. **Continue from clear state**: Don't duplicate completed work

### Avoiding Session Bloat

- Keep delegations focused and atomic
- Don't load unnecessary context (use skills on-demand)
- Complete and close todos regularly
- Commit work incrementally (easier to resume)

## Common Scenarios

The recurring pause/resume scenarios (auto-pause mid-implementation, resuming
after a finalized pause, context warning during research) all reduce to the
same two procedures:

- **Approaching a limit / wrapping up** → follow *PM Response to Context
  Warnings* above, then invoke **`mpm-session-pause`** to persist state.
- **Returning to work** → invoke **`mpm-session-resume`**, which detects the
  pause state, loads the snapshot, and reconciles against git.

Keep delegations atomic and commit incrementally so either procedure resumes
from a clean point.

## Integration with PM Workflow

Session management integrates with standard PM workflow:

```
User Request
    ↓
[Check for session resume state]
    ↓
Research (if needed)
    ↓
[Monitor context usage]
    ↓
Implementation
    ↓
[Auto-pause if 90% reached]
    ↓
Deployment
    ↓
QA
    ↓
Documentation
    ↓
[Final session snapshot if paused]
    ↓
Report Results
```

## Trigger Keywords

- "context", "pause", "resume", "session"
- "token", "limit", "usage"
- "continue", "previous session"
- Auto-loaded at 70%+ context usage
- Auto-loaded when session files exist

## Related Skills

- `mpm-session-pause` - **Procedure**: pause and persist current work state
- `mpm-session-resume` - **Procedure**: load context from a paused session
- `mpm-git-file-tracking` - File tracking during pause/resume
- `mpm-verification-protocols` - Verification state during pause
- `mpm-delegation-patterns` - Resuming delegations mid-workflow
