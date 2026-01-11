---
namespace: mpm/system
command: version
aliases: [mpm-version]
migration_target: /mpm/system:version
category: system
description: Show version information
deprecated: true
deprecated_in: "5.5.0"
replacement: "skill:mpm-version"
---

> **Deprecated:** This command file is deprecated in favor of the `mpm-version` skill.
> For Claude Code 2.1.3+, use the skill-based `/mpm-version` command instead.
> This file is kept for backward compatibility with Claude Code < 2.1.3.

# /mpm-version

Display version information for MPM, agents, and skills.

## Usage
```
/mpm-version
```

Shows project version, build number, all agents (by tier), all skills (by source).

See docs/commands/version.md for details.
