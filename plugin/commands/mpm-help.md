---
description: "Show available MPM commands, agent types, and usage information"
---

# /mpm-help

When the user runs `/mpm-help`, display the following reference information:

## MPM Commands

### CLI Commands (via bash)

| Command | Description |
|---------|-------------|
| `claude-mpm status` | Show active agent sessions |
| `claude-mpm message send <project> <msg>` | Send cross-project message |
| `claude-mpm message list` | List inbox messages |
| `claude-mpm message read <id>` | Read a specific message |
| `claude-mpm doctor` | Diagnose installation issues |
| `claude-mpm configure` | Configure hooks and MCP servers |
| `claude-mpm mcp install` | Install MCP server integrations |
| `claude-mpm info` | Show project and system information |

### Slash Commands (via this plugin)

| Command | Description |
|---------|-------------|
| `/mpm-status` | Check MPM system status |
| `/mpm-help` | Show this help information |

## Agent Types

| Agent | Use For |
|-------|---------|
| **engineer** | Code implementation, refactoring, architecture decisions |
| **research** | Investigation, competitive analysis, information gathering |
| **qa** | Testing, quality assurance, verification, test writing |
| **ops** | Deployment, CI/CD, infrastructure, monitoring |
| **security** | Security audits, vulnerability scanning, OWASP compliance |
| **docs** | Documentation, README updates, API docs, changelogs |
| **data** | Data analysis, database operations, ETL pipelines |
| **design** | UI/UX design, wireframing, design system work |

## MCP Tools

When the `mpm-messaging` MCP server is connected, the following tools are available:

- **message_send** -- Send a message to another project
- **message_list** -- List messages in inbox
- **message_read** -- Read a specific message
- **message_reply** -- Reply to a message
- **message_check** -- Check for new messages
- **message_archive** -- Archive a message
- **shortcut_add** -- Add a project shortcut
- **shortcut_list** -- List project shortcuts
- **shortcut_remove** -- Remove a project shortcut
- **shortcut_resolve** -- Resolve a shortcut to a project path

## Getting Started

If claude-mpm is not yet installed:

```bash
pip install claude-mpm
# or
uv tool install claude-mpm
```

Then run `claude-mpm configure` to set up hooks and MCP servers for your project.
