---
name: mpm-help
description: Display help for Claude MPM commands
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, system, pm-required, documentation]
---

# /mpm-help

Show help for MPM commands. Delegates to PM agent.

## Usage

```
/mpm-help [command]
```

## Examples

```
/mpm-help              # Show all available commands
/mpm-help mpm-init     # Show detailed help for mpm-init
/mpm-help mpm-ticket   # Show ticketing workflow help
```

## What It Provides

- **Command listing**: All available MPM commands
- **Command details**: Syntax, options, and usage examples
- **Delegation patterns**: Which agent handles which command
- **Workflow guidance**: Common command sequences and workflows

See docs/commands/help.md for full command reference.
