---
name: mpm-postmortem
description: Analyze session errors and suggest improvements
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, analysis, pm-recommended]
---

# /mpm-postmortem

Analyze session errors and generate improvement suggestions.

## Usage
```
/mpm-postmortem [--auto-fix] [--create-prs] [--dry-run]
```

Analyzes errors from: scripts, skills, agents, user code.
Generates: fixes, updates, PR recommendations, suggestions.

See docs/commands/postmortem.md for details.
