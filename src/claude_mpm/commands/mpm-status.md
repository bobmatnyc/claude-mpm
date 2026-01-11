---
namespace: mpm/system
command: status
aliases: [mpm-status]
migration_target: /mpm/system:status
category: system
description: Display Claude MPM system status
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm-status"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm-status` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm-status` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# /mpm-status

Show MPM system status. Delegates to PM agent.

## Usage
```
/mpm-status
```

Displays: version, services, agents, memory, configuration, project info.

See docs/commands/status.md for details.
