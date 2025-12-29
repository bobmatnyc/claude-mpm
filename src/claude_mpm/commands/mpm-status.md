---
namespace: mpm/system
command: status
aliases: [mpm-status]
migration_target: /mpm/system:status
category: system
description: Display Claude MPM system status
---
# /mpm-status

Show MPM system status. Delegates to PM agent.

## Usage
```
/mpm-status
```

Displays: version, services, agents, memory, configuration, project info.

See docs/commands/status.md for details.
