---
namespace: mpm
command: main
aliases: [mpm]
migration_target: /mpm
category: system
deprecated_aliases: []
description: Access Claude MPM functionality and manage multi-agent orchestration
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# Claude MPM - Multi-Agent Project Manager

Access Claude MPM functionality and manage your multi-agent orchestration.

Available MPM commands:
- /mpm-agents - Show available agents and versions
- /mpm-doctor - Run diagnostic checks
- /mpm-help - Show command help
- /mpm-status - Show MPM status
- /mpm-ticket - Ticketing workflow management (organize, proceed, status, update, project)
- /mpm-config - Manage configuration
- /mpm-resume - Create session resume files
- /mpm-version - Display version information for project, agents, and skills

Claude MPM extends Claude Code with:
- Multi-agent orchestration
- Project-specific PM instructions
- Agent memory management
- WebSocket monitoring
- Hook system for automation

For more information, use /mpm-help [command]