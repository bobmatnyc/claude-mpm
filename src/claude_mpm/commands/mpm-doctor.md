---
namespace: mpm/system
command: doctor
aliases: [mpm-doctor]
migration_target: /mpm/system:doctor
category: system
description: Run diagnostic checks on Claude MPM installation
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm-doctor"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm-doctor` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm-doctor` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# /mpm-doctor

Run comprehensive diagnostics on Claude MPM installation.

## Usage
```
/mpm-doctor [--verbose] [--fix]
```

Checks: installation, configuration, WebSocket, agents, memory, hooks.

See docs/commands/doctor.md for details.
