---
name: mpm-session-resume
description: Load context from paused session
user-invocable: true
version: "1.2.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
---

# /mpm-session-resume

Load and display context from a paused session, with optional browsing and
selection when multiple sessions exist.

## What This Does

When invoked, this skill:
1. Scans the project-local session store at `.claude-mpm/sessions/` for paused sessions
2. Loads the most recent session (by file modification time) **or** a specific
   session selected with `--select`
3. **Validates** that the session's `project_path` matches the current project — sessions from other projects are skipped
4. Calculates time elapsed since pause and git changes since pause
5. Displays a formatted resume prompt with summary, accomplishments, and next steps
6. Returns the session data so the PM can continue work with full context

> **Note:** Resume always validates that the session belongs to the current project.
> You will never accidentally resume a session from a different project.

## Usage

```
/mpm-session-resume                    # resume most recent session (existing behaviour)
/mpm-session-resume                    # with no args: also lists sessions when >1 exists
/mpm-session-resume --select 2         # resume the 2nd most-recent session (1-based index)
/mpm-session-resume --select 20240101  # resume by partial session ID match
/mpm-session-resume <session-id>       # resume by exact session ID (backward-compatible)
```

**What it shows (listing mode — no args, multiple sessions):**
- Numbered list of sessions, most-recent first
- Session ID (timestamp portion), time elapsed, project name, topic/summary

**What it shows (resume mode):**
- Session summary and time elapsed since pause
- Completed work and current tasks
- Git context and recent commits (new commits since pause)
- **Pending TaskList items** (from Claude Code TaskCreate/TaskList)
- Next recommended actions

## Implementation

**Execute the following Python code.  Parse the user's invocation arguments first,
then dispatch to the appropriate code path.**

```python
import sys
from pathlib import Path

try:
    from claude_mpm.services.cli.session_resume_helper import SessionResumeHelper
except ImportError:
    print(
        "ERROR: claude_mpm is not importable in the current Python environment.\n"
        "If you installed via 'uv tool install claude-mpm', run:\n"
        "  uv run python -c 'from claude_mpm.services.cli.session_resume_helper "
        "import SessionResumeHelper'\n"
        "Or invoke directly: claude-mpm session-resume\n"
        "Alternatively, activate the virtual environment where claude-mpm is installed."
    )
    raise SystemExit(1)

# --------------------------------------------------------------------------
# Argument parsing
# Invocation forms:
#   /mpm-session-resume                    → list_mode=True if >1 session, else resume most recent
#   /mpm-session-resume --select <value>   → select by index or partial ID
#   /mpm-session-resume <session-id>       → exact session-id (backward-compatible)
# --------------------------------------------------------------------------

# The skill receives user arguments via the 'args' variable set by the harness,
# or you can parse from the invocation line.  Use whichever is available.
# For safety, default to an empty list if 'args' is not defined.
try:
    raw_args = args  # type: ignore[name-defined]  # set by skill harness
except NameError:
    raw_args = []

select_value: str | None = None
exact_session_id: str | None = None

i = 0
while i < len(raw_args):
    token = str(raw_args[i])
    if token == "--select" and i + 1 < len(raw_args):
        select_value = str(raw_args[i + 1])
        i += 2
    elif not token.startswith("--"):
        exact_session_id = token
        i += 1
    else:
        i += 1

# --------------------------------------------------------------------------
# Create helper scoped to the current project.
# --------------------------------------------------------------------------
helper = SessionResumeHelper(project_path=Path.cwd())

# --------------------------------------------------------------------------
# Dispatch
# --------------------------------------------------------------------------

if select_value is not None:
    # --select <index-or-partial-id>
    session_data, error_msg = helper.resolve_session_by_selection(select_value)
    if session_data is None:
        print(error_msg)
    else:
        prompt_text = helper.format_resume_prompt(session_data)
        print(prompt_text)
        session_id = session_data.get("session_id", "unknown")
        file_path = session_data.get("file_path")
        print(f"Loaded session: {session_id}")
        if file_path:
            print(f"Source: {file_path}")

elif exact_session_id is not None:
    # Exact session ID supplied (backward-compatible form).
    all_sessions = helper.list_all_sessions()
    matched = [
        s for s in all_sessions
        if s.get("session_id") == exact_session_id
    ]
    if not matched:
        print(f"No session found with ID: {exact_session_id}")
        print("")
        print(helper.format_session_list())
    else:
        session_data = matched[0]
        prompt_text = helper.format_resume_prompt(session_data)
        print(prompt_text)
        file_path = session_data.get("file_path")
        print(f"Loaded session: {exact_session_id}")
        if file_path:
            print(f"Source: {file_path}")

else:
    # No arguments — list when multiple sessions exist, else resume most recent.
    session_count = helper.get_session_count()
    if session_count == 0:
        print("No paused sessions found for this project in .claude-mpm/sessions/")
        print("")
        print("To create a paused session, use: /mpm-pause")
    elif session_count > 1:
        # Show numbered list so the user can pick.
        print(helper.format_session_list())
        print("")
        print("Resuming the most recent session automatically…")
        session_data = helper.check_and_display_resume_prompt()
        if session_data:
            session_id = session_data.get("session_id", "unknown")
            file_path = session_data.get("file_path")
            print(f"Loaded session: {session_id}")
            if file_path:
                print(f"Source: {file_path}")
    else:
        # Only one session — resume it directly (existing behaviour).
        session_data = helper.check_and_display_resume_prompt()
        if session_data is None:
            print("No paused sessions found for this project in .claude-mpm/sessions/")
            print("")
            print("To create a paused session, use: /mpm-pause")
        else:
            session_id = session_data.get("session_id", "unknown")
            file_path = session_data.get("file_path")
            print(f"")
            print(f"Loaded session: {session_id}")
            if file_path:
                print(f"Source: {file_path}")
```

## Session Storage Location

**Session location:** project-local `.claude-mpm/sessions/session-*.md` (and `.json`/`.yaml`)

Sessions are stored relative to the project root so each project has its own
isolated session history. Resume always validates that the session belongs to
the current project — you will never accidentally load a session from another
checkout.

The store contains:
```
<project-root>/.claude-mpm/sessions/
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
