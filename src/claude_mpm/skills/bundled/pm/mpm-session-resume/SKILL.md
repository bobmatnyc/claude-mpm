---
name: mpm-session-resume
description: Load context from paused session
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, session, pm-recommended]
---

# /mpm-session-resume

Load and display context from most recent paused session.

## Usage
```
/mpm-resume
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
