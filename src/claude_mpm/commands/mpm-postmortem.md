---
namespace: mpm/analysis
command: postmortem
aliases: [mpm-postmortem]
migration_target: /mpm/analysis:postmortem
category: analysis
description: Analyze session errors and suggest improvements
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
