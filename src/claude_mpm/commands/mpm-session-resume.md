---
namespace: mpm/session
command: resume
aliases: [mpm-session-resume]
migration_target: /mpm/session:resume
category: session
description: Load context from paused session
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

**Session location:** `.claude-mpm/sessions/session-*.json`

**Token usage:** ~20-40k tokens (10-20% of context budget)

**Note:** Reads existing sessions (created automatically at 70% context). Does NOT create new files.

See docs/features/session-auto-resume.md for details.
