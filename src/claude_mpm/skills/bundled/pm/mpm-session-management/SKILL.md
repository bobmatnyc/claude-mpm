# PM Session Management

**Type**: Framework
**Applies To**: Project Manager Agent
**Load Priority**: On-demand (context limit or session resume)

## Purpose

This skill provides session pause/resume capabilities for the PM when context limits are approaching or when resuming from a previous session. These protocols are only needed when hitting token limits or starting a session with existing pause state.

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

### At Session Start, PM Checks For

**1. Active Incremental Pause**: `.claude-mpm/sessions/ACTIVE-PAUSE.jsonl`

If found:
- Display warning with action count and context percentage
- Options:
  - **Continue**: Resume work from pause state
  - **Finalize**: Run `/mpm-init pause --finalize` to create snapshot
  - **Discard**: Start fresh (previous work still in git)

**Example Response**:
```
⚠️ Active session pause detected

Actions recorded: 47
Context usage: ~92%

Options:
1. Continue working (actions will be recorded)
2. Finalize pause: /mpm-init pause --finalize
3. Discard pause: Delete .claude-mpm/sessions/ACTIVE-PAUSE.jsonl

Would you like to continue from the paused session?
```

**2. Finalized Pause**: `.claude-mpm/sessions/LATEST-SESSION.txt`

If found:
- Display resume context with accomplishments and next steps
- Load context from the session snapshot
- Continue where previous session left off

**Example Response**:
```
📋 Resuming from previous session

Last session accomplished:
- ✅ Implemented OAuth2 authentication (Engineer)
- ✅ Deployed to staging (Vercel-ops)
- ⏸️ QA verification in progress

Next steps:
- Complete QA verification of auth flow
- Update documentation
- Deploy to production

Continue with QA verification?
```

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

### Scenario 1: Auto-Pause During Implementation

```
Context: 90% during Engineer delegation

PM Actions:
1. Wait for Engineer to complete current file
2. Track files immediately (git add + commit)
3. Update todo with completion status
4. Create summary of implementation state
5. Session pauses, all recorded in ACTIVE-PAUSE.jsonl

Next Session:
1. PM detects ACTIVE-PAUSE.jsonl
2. Continues from implementation state
3. Proceeds to QA verification phase
```

### Scenario 2: Resume After Finalized Pause

```
Context: User returns to continue work

PM Actions:
1. Detects LATEST-SESSION.txt
2. Loads session-{timestamp}.md for human summary
3. Loads session-{timestamp}.json for full state
4. Checks git log for verification
5. Presents summary to user
6. Continues workflow from next phase
```

### Scenario 3: Context Warning During Research

```
Context: 75% during Research agent investigation

PM Actions:
1. Allow Research to complete current investigation
2. Don't start new research tasks
3. Collect Research findings
4. Document findings in session state
5. Prepare for potential pause at 90%

If 90% reached:
1. Research findings already documented
2. Implementation can start in next session
3. Clear handoff context available
```

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

- `mpm-git-file-tracking` - File tracking during pause/resume
- `mpm-verification-protocols` - Verification state during pause
- `mpm-delegation-patterns` - Resuming delegations mid-workflow
