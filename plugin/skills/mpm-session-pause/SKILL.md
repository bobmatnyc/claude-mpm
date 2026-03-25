---
name: mpm-session-pause
description: Pause session and save current work state for later resume
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
---

# /mpm-pause

Pause the current session and save all work state for later resume.

## What This Does

When invoked, this skill:
1. Captures current work state (todos, git status, context summary)
2. Creates session file at `.claude-mpm/sessions/session-{timestamp}.md`
3. Updates `.claude-mpm/sessions/LATEST-SESSION.txt` pointer
4. Optionally commits session state to git
5. Shows user the session file path for later resume

## Usage

```
/mpm-pause [optional message describing current work]
```

**Examples:**
```
/mpm-pause
/mpm-pause Working on authentication refactor, about to test login flow
/mpm-pause Need to context switch to urgent bug fix
```

## Implementation

**Execute the following Python code to pause the session:**

```python
from pathlib import Path
from claude_mpm.services.cli.session_pause_manager import SessionPauseManager

# Optional: Get message from user's command
# If user provided message after /mpm-pause, extract it
# Otherwise, message = None

# Create session pause manager
manager = SessionPauseManager(project_path=Path.cwd())

# Create pause session
session_id = manager.create_pause_session(
    message=message,  # Optional context message
    skip_commit=False,  # Will commit to git if in a repo
    export_path=None,  # No additional export needed
)

# Report success to user
print(f"✅ Session paused successfully!")
print(f"")
print(f"Session ID: {session_id}")
print(f"Session files:")
print(f"  - .claude-mpm/sessions/{session_id}.md (human-readable)")
print(f"  - .claude-mpm/sessions/{session_id}.json (machine-readable)")
print(f"  - .claude-mpm/sessions/{session_id}.yaml (config format)")
print(f"")
print(f"Quick resume:")
print(f"  /mpm-resume")
print(f"")
print(f"View session context:")
print(f"  cat .claude-mpm/sessions/LATEST-SESSION.txt")
print(f"  cat .claude-mpm/sessions/{session_id}.md")
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

All session files are stored in:
```
.claude-mpm/sessions/
├── LATEST-SESSION.txt          # Pointer to most recent session
├── session-YYYYMMDD-HHMMSS.md
├── session-YYYYMMDD-HHMMSS.json
└── session-YYYYMMDD-HHMMSS.yaml
```

## Token Budget

**Token usage:** ~5-10k tokens to execute (2-5% of context budget)

**Benefit:** Saves all remaining context for future resume, allowing you to:
- Context switch to urgent tasks
- Take a break and resume later
- Archive current work state before major changes

## Resume Later

To resume this session:
```
/mpm-resume
```

Or manually:
```bash
cat .claude-mpm/sessions/LATEST-SESSION.txt
cat .claude-mpm/sessions/session-YYYYMMDD-HHMMSS.md
```

## Git Integration

If in a git repository, the session will be automatically committed with message:
```
session: pause at YYYY-MM-DD HH:MM:SS

Session ID: session-YYYYMMDD-HHMMSS
Context: [your optional message]
```

## Use Cases

**Context switching:**
```
/mpm-pause Switching to urgent production bug
```

**End of work session:**
```
/mpm-pause Completed API refactor, ready for testing tomorrow
```

**Before major changes:**
```
/mpm-pause Saving state before attempting risky refactor
```

**When approaching context limit:**
```
/mpm-pause Hit 150k tokens, starting fresh session
```

## Related Commands

- `/mpm-resume` - Resume from most recent paused session
- `/mpm-init resume` - Alternative resume command
- See `docs/features/session-auto-resume.md` for auto-pause behavior

## Notes

- Session files are project-local (not synced across machines)
- Git commit is optional (automatically skipped if not a repo)
- LATEST-SESSION.txt always points to most recent session
- Session format compatible with auto-pause feature (70% context trigger)
