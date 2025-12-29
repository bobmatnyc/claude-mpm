---
namespace: mpm/system
command: doctor
aliases: [mpm-doctor]
migration_target: /mpm/system:doctor
category: system
description: Run diagnostic checks on Claude MPM installation
---
# /mpm-doctor

Run comprehensive diagnostics on Claude MPM installation.

## Usage
```
/mpm-doctor [--verbose] [--fix]
```

Checks: installation, configuration, WebSocket, agents, memory, hooks.

See docs/commands/doctor.md for details.
