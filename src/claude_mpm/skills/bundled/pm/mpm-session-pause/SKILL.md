---
name: mpm-session-pause
description: Pause session and save current work state for later resume
user-invocable: true
version: "1.4.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
effort: medium
---

# /mpm-session-pause

Pause the current session and save all work state for later resume.

## What This Does

When invoked, this skill:
1. Captures current work state (todos, git status, context summary)
2. Creates session files at `.claude-mpm/sessions/session-{timestamp}.*` (project-local)
3. Updates `.claude-mpm/sessions/LATEST-SESSION.txt` pointer
4. Shows the session file path for later resume

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

## Implementation

Run the console script directly — no interpreter resolution needed:

```bash
# Basic pause
claude-mpm session pause

# With a descriptive message
claude-mpm session pause -m "End of day — auth refactor in progress"

# Export a copy to a specific location
claude-mpm session pause --export /tmp/session-backup.json
```

If the user provided a message after `/mpm-session-pause`, pass it via `-m`:

```bash
claude-mpm session pause -m "<user message here>"
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

## Session File Location

All session files are stored in the **project-local** directory:
```
<project-root>/.claude-mpm/sessions/
├── LATEST-SESSION.txt          # Pointer to most recent session
├── session-YYYYMMDD-HHMMSS.md
└── session-YYYYMMDD-HHMMSS.json
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

Or from the CLI:
```bash
claude-mpm session resume
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

- `/mpm-session-resume` — Resume from most recent paused session
- `claude-mpm session resume` — CLI entry point for resume
- `claude-mpm session pause --help` — Full CLI usage

## Notes

- Session files are stored project-locally in `.claude-mpm/sessions/` (not synced across machines)
- Add `.claude-mpm/sessions/` to `.gitignore`
- No git commit is created — sessions live outside version control
- LATEST-SESSION.txt always points to most recent session in the current project
- Session format compatible with auto-pause feature (70% context trigger)
