---
name: mpm-session-pause
description: Pause session and save current work state for later resume
user-invocable: true
version: "1.1.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
effort: medium
---

# /mpm-session-pause

Pause the current session and save all work state for later resume.

## What This Does

When invoked, this skill:
1. Captures current work state (todos, git status, context summary)
2. Creates session file at `.claude-mpm/sessions/session-{timestamp}.md` (project-local)
3. Updates `.claude-mpm/sessions/LATEST-SESSION.txt` pointer
4. Optionally commits session state to git
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

## Implementation

### Step 0 — Resolve the correct Python interpreter (REQUIRED)

`claude_mpm` may be installed in an **isolated** environment (pipx, `uv tool`,
`pip --user`) that the system `python3` **cannot** import. Running bare
`python3 -c "from claude_mpm..."` then fails with `ModuleNotFoundError`.

**Before running any Python below, resolve the interpreter that owns the
installed `claude-mpm`.** Run this shell snippet and use the captured value
(`$MPM_PY`) as your interpreter:

```bash
# Honor an explicit override first, then ask claude_mpm to resolve itself,
# then fall back to the venv python beside the claude-mpm console script.
if [ -n "$CLAUDE_MPM_PYTHON" ]; then
    MPM_PY="$CLAUDE_MPM_PYTHON"
else
    MPM_PY="$(python3 -m claude_mpm.utils.interpreter_resolver 2>/dev/null)"
    if [ -z "$MPM_PY" ]; then
        # Derive the venv python from the installed claude-mpm executable.
        CMPM="$(command -v claude-mpm 2>/dev/null)"
        if [ -n "$CMPM" ]; then
            MPM_PY="$(dirname "$(readlink -f "$CMPM" 2>/dev/null || echo "$CMPM")")/python"
        fi
    fi
    [ -x "$MPM_PY" ] || MPM_PY="$(command -v python3)"
fi
echo "Using interpreter: $MPM_PY"
```

Then run the pause code with **`$MPM_PY`** (NOT bare `python3`):
`"$MPM_PY" - <<'PY' ... PY`

**Execute the following Python code to pause the session:**

```python
from pathlib import Path

try:
    from claude_mpm.services.cli.session_pause_manager import SessionPauseManager
except ImportError:
    print(
        "ERROR: claude_mpm is not importable in the current Python environment.\n"
        "Resolve the correct interpreter first (see Step 0 above), e.g.:\n"
        "  MPM_PY=\"$(python3 -m claude_mpm.utils.interpreter_resolver)\"\n"
        "  \"$MPM_PY\" -c 'from claude_mpm.services.cli.session_pause_manager "
        "import SessionPauseManager'\n"
        "Or set CLAUDE_MPM_PYTHON to the interpreter where claude-mpm is installed.\n"
        "Alternatively, invoke directly: claude-mpm session-pause"
    )
    raise SystemExit(1)

# Optional: Get message from user's command
# If user provided message after /mpm-session-pause, extract it
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
print(f"  /mpm-session-resume")
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
