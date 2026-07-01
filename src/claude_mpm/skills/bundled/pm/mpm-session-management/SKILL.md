---
version: "1.1.1"
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

- Context usage reaches 70%+ thresholds (informational warnings only)
- Session starts with `.claude-mpm/sessions/LATEST-SESSION.txt`
- User runs `/mpm-session-resume`

## Context Usage Monitoring

The MPM framework continuously tracks context usage and provides informational warnings as usage approaches limits. Context-usage auto-pause (which used to abort sessions at 90% usage) was disabled in commit da5166603 (PR #646) to preserve legitimate active work.

### Threshold Levels and Warnings

| Level | Usage | Behavior |
|-------|-------|----------|
| Caution | 70% | Informational warning: "Context usage at 70%. Consider wrapping up current work." |
| Warning | 85% | Informational warning: "Context usage at 85%. Session nearing capacity." |
| Auto-Pause Disabled | 90% | Informational warning: "Context usage at 90%. Consider wrapping up or running /compact (auto-pause is disabled)." |
| Critical | 95% | Informational warning: "Context usage at 95%. Consider wrapping up or running /compact (auto-pause is disabled)." |

Crossing these thresholds **only produces informational warnings**. No session pause is triggered, no ACTIVE-PAUSE.jsonl file is created. Sessions continue normally.

### Manual Session Pause

To save session state before context limits:

1. Use the **`/mpm-session-pause`** skill to explicitly create a session snapshot
2. This captures git state, todos, task list, and accomplishments into `.claude-mpm/sessions/session-{timestamp}.*` files
3. Sessions are stored in project-local `.claude-mpm/sessions/` directory (not synced across machines)

## Session Resume Protocol

> **Procedure.** The step-by-step resume flow now lives in **`mpm-session-resume`**.
> Invoke that skill to load and display context from a paused session.

When resuming work:

1. Use **`/mpm-session-resume`** to load the most recent paused session
2. The skill detects `.claude-mpm/sessions/LATEST-SESSION.txt` and loads the associated snapshot
3. Session accomplishments, pending tasks, and git context are displayed
4. PM can continue work with full prior context

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

Sessions are stored project-locally in `.claude-mpm/sessions/`:

```
.claude-mpm/sessions/
├── LATEST-SESSION.txt       # Pointer to most recent paused session
├── session-YYYYMMDD-HHMMSS.json   # Machine-readable session snapshots
└── session-YYYYMMDD-HHMMSS.md     # Human-readable markdown summary
```

### File Purposes

- **LATEST-SESSION.txt**: Points to most recent finalized session file
- **session-*.json**: Complete session state (todos, git status, accomplishments, next steps)
- **session-*.md**: Human-readable summary for quick review

Sessions are created manually via `/mpm-session-pause` skill. The ACTIVE-PAUSE.jsonl file (used during auto-pause) is no longer created since auto-pause is disabled.

## Best Practices

### When Context Limits Approach

1. **Monitor warnings**: When you see context warnings (70%+), begin wrapping up
2. **Finish current phase**: Complete the delegation in progress
3. **Update todos**: Ensure all todos reflect current status
4. **Create session snapshot**: Invoke `/mpm-session-pause` to save state for later resume
5. **Create handoff context**: Document what's completed and what remains

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

Session pause/resume scenarios reduce to two procedures:

- **Approaching context limits / wrapping up** → Follow the "PM Response to Context Warnings" protocol above, then invoke **`/mpm-session-pause`** to create a session snapshot that persists your work state.
- **Returning to work** → Invoke **`/mpm-session-resume`**, which loads the most recent paused session snapshot and displays prior accomplishments, pending tasks, and git context.

Keep delegations atomic and commit incrementally so either procedure resumes from a clean point.

## Integration with PM Workflow

Session management integrates with standard PM workflow:

```
User Request
    ↓
[Check for session resume state]
    ↓
Research (if needed)
    ↓
[Monitor context usage — watch for warnings]
    ↓
Implementation
    ↓
[Approaching limit? → /mpm-session-pause]
    ↓
Deployment
    ↓
QA
    ↓
Documentation
    ↓
[Save session snapshot if context is high]
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
