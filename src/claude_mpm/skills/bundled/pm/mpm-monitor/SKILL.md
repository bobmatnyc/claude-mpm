---
name: mpm-monitor
description: Control monitoring server and dashboard
user-invocable: true
version: "1.0.0"
category: mpm-command
tags: [mpm-command, system, pm-optional]
---

# /mpm-monitor

Manage Socket.IO monitoring server for real-time dashboard.

## Usage
```
/mpm-monitor [start|stop|restart|status|port] [options]
```

**Subcommands:**
- `start`: Start server (auto-selects port 8765-8785)
- `stop`: Stop running server
- `status`: Show server status
- `port <PORT>`: Start on specific port

**Key Options:**
- `--port PORT`: Specific port
- `--force`: Force kill to reclaim port
- `--foreground`: Run in foreground (default: background)

Dashboard: http://localhost:8766

See docs/commands/monitor.md for details.
