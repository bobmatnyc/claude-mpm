---
name: mpm-session-resume
description: Load context from paused session
user-invocable: true
version: "1.1.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
---

# /mpm-session-resume

Load and display context from the most recent paused session.

## What This Does

When invoked, this skill:
1. Scans the global session store at `~/.claude-mpm/sessions/` for paused sessions
2. Loads the most recent session (by file modification time)
3. Calculates time elapsed since pause and git changes since pause
4. Displays a formatted resume prompt with summary, accomplishments, and next steps
5. Returns the session data so the PM can continue work with full context

## Usage

```
/mpm-resume
```

**What it shows:**
- Session summary and time elapsed since pause
- Completed work and current tasks
- Git context and recent commits (new commits since pause)
- **Pending TaskList items** (from Claude Code TaskCreate/TaskList)
- Next recommended actions

## Implementation

**Execute the following Python code to load and display the paused session:**

```python
from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper

# Create resume helper — NO arguments.
# The helper defaults to the global session store at ~/.claude-mpm/sessions/
# so it finds pause files regardless of the current working directory.
helper = SessionResumeHelper()

# Check for paused sessions and display the resume prompt.
# This prints the formatted context and returns the session data dict.
session_data = helper.check_and_display_resume_prompt()

if session_data is None:
    print("No paused sessions found in ~/.claude-mpm/sessions/")
    print("")
    print("To create a paused session, use: /mpm-pause")
else:
    # Session data is now loaded — PM continues from here using
    # the displayed context (summary, accomplishments, next steps,
    # git changes, and pending tasks).
    session_id = session_data.get("session_id", "unknown")
    file_path = session_data.get("file_path")
    print(f"")
    print(f"Loaded session: {session_id}")
    if file_path:
        print(f"Source: {file_path}")
```

## Session Storage Location

**Global store:** `~/.claude-mpm/sessions/`

Sessions are stored in a fixed user-global location — NOT relative to the current working directory. This ensures that resume finds paused sessions no matter which project directory you invoke `/mpm-resume` from.

The store contains:
```
~/.claude-mpm/sessions/
├── LATEST-SESSION.txt                  # Pointer to most recent session
├── session-YYYYMMDD-HHMMSS.md          # Human-readable
├── session-YYYYMMDD-HHMMSS.json        # Machine-readable (loaded by resume)
└── session-YYYYMMDD-HHMMSS.yaml        # Config format
```

Resume reads the `.json` file (authoritative machine-readable format). The `.md` file is for humans; resume will not attempt to parse it as JSON.

## Token Budget

**Token usage:** ~20-40k tokens (10-20% of context budget)

This loads the session summary, accomplishments, next steps, git history, and pending task list into context so the PM can continue work without rediscovering state.

## What Gets Loaded

**From the paused session:**
- Session ID and pause timestamp
- Project path (recorded at pause time, for display only)
- Git branch, recent commits, and file status at pause
- Summary, accomplishments, and next steps
- TaskList state (pending/in-progress tasks)
- Context message (if provided at pause)

**Calculated at resume time:**
- Human-readable time elapsed (e.g., "2 hours ago", "3 days ago")
- Git commits added since pause
- File changes since pause

## Notes

- Reads existing sessions only. Does NOT create new files.
- Auto-pause at 70% context creates sessions automatically; this skill reads them.
- Session files are kept after resume (not auto-deleted) so you can resume multiple times.
- To clear a session after resume, call `helper.clear_session(session_data)` explicitly.

## Related Commands

- `/mpm-pause` - Pause current session and save state
- `/mpm-init resume` - Alternative resume entry point

See `docs/features/session-auto-resume.md` for auto-pause behavior.
