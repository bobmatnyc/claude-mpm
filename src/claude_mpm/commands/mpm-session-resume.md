---
namespace: mpm/session
command: resume
aliases: [mpm-session-resume]
migration_target: /mpm/session:resume
category: session
description: Load context from paused session
deprecated: true
deprecated_in: "5.5.0"
replacement: "cli:claude-mpm session resume"
---

> **Deprecated:** This command file is kept for backward compatibility with Claude Code < 2.1.3.
> Use `claude-mpm session resume` (the stable console-script entry point) or the
> `/mpm-session-resume` skill instead.

# /mpm-session-resume

Load and display context from most recent paused session.

## Usage

Invoke via the CLI — no interpreter resolution needed:

```bash
# Resume most recent session
claude-mpm session resume

# Resume 2nd most recent
claude-mpm session resume --select 2

# Resume by partial session ID
claude-mpm session resume --select 20240101

# Resume by exact session ID
claude-mpm session resume session-20240101-143022
```

**What it shows:**
- Session summary and time elapsed
- Completed work and current tasks
- Git context and recent commits
- Next recommended actions

**Session location:** `.claude-mpm/sessions/session-*.md`

**Token usage:** ~20-40k tokens (10-20% of context budget)

**Note:** Reads existing sessions (created automatically at 70% context). Does NOT create new files.

See docs/features/session-auto-resume.md for details.
