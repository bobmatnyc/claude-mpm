---
namespace: mpm/analysis
command: postmortem
aliases: [mpm-postmortem]
migration_target: /mpm/analysis:postmortem
category: analysis
description: Analyze session errors and suggest improvements
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm-postmortem"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm-postmortem` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm-postmortem` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# /mpm-postmortem

Analyze session errors and generate improvement suggestions.

## Usage
```
/mpm-postmortem [--auto-fix] [--create-prs] [--dry-run]
```

Analyzes errors from: scripts, skills, agents, user code.
Generates: fixes, updates, PR recommendations, suggestions.

See docs/commands/postmortem.md for details.
