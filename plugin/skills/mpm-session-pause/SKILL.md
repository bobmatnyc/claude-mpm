---
name: mpm-session-pause
description: Pause session and save current work state for later resume
user-invocable: true
version: "1.5.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
---

# /mpm-session-pause

Pause the current session and save all work state for later resume.

## What This Does

When invoked, this skill:
1. Captures current work state (todos, git status, context summary)
2. Creates session files at `.claude-mpm/sessions/session-{timestamp}.*` (project-local)
3. Updates `.claude-mpm/sessions/LATEST-SESSION.txt` pointer
4. **Prunes stale git worktrees** under `<repo>/.claude/worktrees/` (see Worktree
   Pruning section below)
5. Shows user the session file path for later resume

## Usage

```
/mpm-session-pause [optional message describing current work]
```

**Examples:**
```
/mpm-session-pause
/mpm-session-pause Working on authentication refactor, about to test login flow
/mpm-session-pause Need to context switch to urgent bug fix
```

## Worktree Pruning (issue #892)

At pause time, MPM automatically prunes stale agent worktrees under
`<repo>/.claude/worktrees/`.

**Safety classification** — a worktree is PRESERVED if ANY of the following is
true:
- It has uncommitted changes (staged or unstaged).
- It has untracked files.
- Its branch has commits not yet merged into the main branch (or not pushed to
  its upstream remote).
- It is marked as locked by git.
- Any git command fails (fail-safe: when in doubt, PRESERVE).

Only worktrees that are provably clean and fully merged are removed.

**Output** — after the session files are written, the pause command prints:

```
Worktree Cleanup:
  Pruned 2 stale worktree(s)
  Preserved 1 worktree(s) with unsaved work
    /repo/.claude/worktrees/agent-abc: branch has commits not merged into main branch
```

**Opt-out** — pass `--no-prune-worktrees` to the CLI to skip:

```bash
claude-mpm session pause --no-prune-worktrees
```

## Implementation

Run the console script directly:

```bash
# Basic pause (includes worktree pruning)
claude-mpm session pause

# With a descriptive message
claude-mpm session pause -m "End of day — auth refactor in progress"

# Skip worktree pruning
claude-mpm session pause --no-prune-worktrees

# Export a copy to a specific location
claude-mpm session pause --export /tmp/session-backup.json
```

Or invoke programmatically:

```python
from pathlib import Path
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

manager = SessionPauseManager(project_path=Path.cwd())

# Default: pruning enabled
session_id = manager.create_pause_session(
    message="End of day",
    prune_worktrees=True,   # set False to skip pruning
)
print(f"Session ID: {session_id}")
```

## What Gets Saved

**Session State:**
- Session ID and timestamp
- Current working directory
- Git branch, recent commits, and file status
- Primary task and current phase
- Context message (if provided)
- **TaskList state** (pending/in-progress tasks from Claude Code)

**Resume Instructions:**
- Quick-start commands
- Validation commands
- Files to review

**File Formats:**
- `.md` - Human-readable markdown (for reading)
- `.json` - Machine-readable (for tooling)
- `.yaml` - Human-readable config (for editing)

## Session File Location

All session files are stored in the **project-local** directory:
```
<project-root>/.claude-mpm/sessions/
├── LATEST-SESSION.txt          # Pointer to most recent session
├── session-YYYYMMDD-HHMMSS.md
├── session-YYYYMMDD-HHMMSS.json
└── session-YYYYMMDD-HHMMSS.yaml
```

This ensures sessions are scoped to the project that created them — pausing in
project A and opening project B will never load project A's session state.

## Token Budget

**Token usage:** ~5-10k tokens to execute (2-5% of context budget)

**Benefit:** Saves all remaining context for future resume, allowing you to:
- Context switch to urgent tasks
- Take a break and resume later
- Archive current work state before major changes

## Resume Later

To resume this session:
```
/mpm-session-resume
```

Or manually:
```bash
cat .claude-mpm/sessions/LATEST-SESSION.txt
cat .claude-mpm/sessions/session-YYYYMMDD-HHMMSS.md
```

## Git Integration

Session files are stored in the project-local `.claude-mpm/sessions/` directory.
Add this directory to your `.gitignore` — session state is machine-specific and
should not be committed. No git commit is created by the pause operation.

## Use Cases

**Context switching:**
```
/mpm-session-pause Switching to urgent production bug
```

**End of work session:**
```
/mpm-session-pause Completed API refactor, ready for testing tomorrow
```

**Before major changes:**
```
/mpm-session-pause Saving state before attempting risky refactor
```

**When approaching context limit:**
```
/mpm-session-pause Hit 150k tokens, starting fresh session
```

## Related Commands

- `/mpm-session-resume` - Resume from most recent paused session
- `/mpm-init resume` - Alternative resume command
- See `docs/features/session-auto-resume.md` for auto-pause behavior

## Notes

- Session files are stored project-locally in `.claude-mpm/sessions/` (not synced across machines)
- Add `.claude-mpm/sessions/` to `.gitignore`
- No git commit is created — sessions live outside version control
- LATEST-SESSION.txt always points to most recent session in the current project
- Session format compatible with auto-pause feature (70% context trigger)
