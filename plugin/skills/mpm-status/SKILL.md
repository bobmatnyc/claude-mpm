---
name: mpm-status
description: Display Claude MPM system status
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, system, pm-required, diagnostics]
---

# /mpm-status

Show MPM system status. Delegates to PM agent.

## Usage

```
/mpm-status
```

## What It Shows

Displays comprehensive system information:
- **Version**: MPM version and installation details
- **Services**: WebSocket server status, monitoring dashboard
- **Agents**: Available agents and their versions
- **Memory**: Memory system statistics and health
- **Configuration**: Current MPM configuration settings
- **Project Info**: Project-specific context and setup

## When to Use

- Check if MPM is properly installed and configured
- Verify agent availability before delegation
- Debug system issues or unexpected behavior
- Get quick overview of system health

See docs/commands/status.md for details.
