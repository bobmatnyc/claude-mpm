---
name: mpm-session-resume
description: Load context from paused session
user-invocable: true
version: "1.4.1"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
effort: medium
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

Run the console script directly — no interpreter resolution needed:

```bash
# Resume most recent session (lists if multiple exist)
claude-mpm session resume

# Resume the 2nd most recent session
claude-mpm session resume --select 2

# Resume by partial session ID (date prefix)
claude-mpm session resume --select 20240101

# Resume by exact session ID
claude-mpm session resume session-20240101-143022
```

> **Permission note (Bug #735):** Do **not** probe for sessions with
> `ls .claude-mpm/sessions/ 2>/dev/null` — that swallows stderr, so a
> permission-denied read looks identical to "no sessions" and resume wrongly
> reports nothing to resume. The `claude-mpm session resume` command handles
> this correctly via `check_session_dir_access()`.

### If `claude-mpm session resume` fails

If the command exits non-zero, capture the full error and show it verbatim —
do **not** summarise with a generic "not importable" message:

```bash
claude-mpm session resume 2>&1
rc=$?
if [ "$rc" -ne 0 ]; then
    echo ""
    echo "ERROR: claude-mpm session resume failed (exit $rc)."
    echo "Full error shown above."
    echo ""
    echo "Diagnostic steps:"
    echo "  1. Verify claude-mpm is on PATH:  command -v claude-mpm"
    echo "  2. Check the actual import error:  python3 -c 'import claude_mpm' 2>&1"
    echo "  3. If a transitive dep fails (e.g. shadowed stdlib module), check"
    echo "     sys.path[0] is not /tmp:  python3 -c 'import sys; print(sys.path[0])'"
fi
```

> **Note on misleading ImportError messages (issue #781):** A bare
> `except ImportError` can fire for transitive failures (e.g. a stray
> `/tmp/bisect.py` shadowing stdlib `bisect`) unrelated to `claude_mpm`
> itself. Always inspect the **actual** exception — `e.name` tells you
> which module failed. If `e.name` does not start with `claude_mpm`, the
> problem is a shadowed or missing transitive dependency, not a missing
> `claude_mpm` installation.

## Session Storage Location

**Session location:** project-local `.claude-mpm/sessions/session-*.md` (and `.json`)

Sessions are stored relative to the project root so each project has its own
isolated session history. Resume always validates that the session belongs to
the current project — you will never accidentally load a session from another
checkout.

The store contains:
```
<project-root>/.claude-mpm/sessions/
├── LATEST-SESSION.txt                  # Pointer to most recent session
├── session-YYYYMMDD-HHMMSS.md          # Human-readable
└── session-YYYYMMDD-HHMMSS.json        # Machine-readable (loaded by resume)
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

## Related Commands

- `/mpm-session-pause` — Pause current session and save state
- `claude-mpm session pause` — CLI entry point for pause
- `claude-mpm session resume --help` — Full CLI usage

See `docs/features/session-auto-resume.md` for auto-pause behavior.
