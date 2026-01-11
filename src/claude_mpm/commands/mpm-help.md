---
namespace: mpm/system
command: help
aliases: [mpm-help]
migration_target: /mpm/system:help
category: system
description: Display help for Claude MPM commands
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm-help"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm-help` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm-help` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# /mpm-help

Show help for MPM commands. Delegates to PM agent.

## Usage
```
/mpm-help [command]
```

Shows all commands or detailed help for specific command.

See docs/commands/help.md for full command reference.
