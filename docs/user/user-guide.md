---
title: User Guide
version: 4.21.1
last_updated: 2025-11-09
status: current
---

# User Guide

A concise guide to Claude MPM features and daily workflows.

## Table of Contents

- [Auto-Configuration](#auto-configuration)
- [Configuration](#configuration)
- [Agent System](#agent-system)
- [Ticketing Workflows](#ticketing-workflows)
- [Skills System](#skills-system)
- [Memory System](#memory-system)
- [Local Process Management](#local-process-management)
- [Session Management](#session-management)
- [Real-Time Monitoring](#real-time-monitoring)
- [MCP Gateway](#mcp-gateway)
- [Best Practices](#best-practices)

## Auto-Configuration

Auto-configure detects your stack and deploys a baseline agent set.

```bash
claude-mpm auto-configure
claude-mpm auto-configure --preview
claude-mpm auto-configure --threshold 60
```

See [Auto-Configuration](../getting-started/auto-configuration.md) for details.

## Configuration

Claude MPM reads configuration in this priority order:

1. CLI args
2. Environment variables
3. Project config: `.claude-mpm/config.yaml`
4. User config: `~/.claude-mpm/config.yaml`
5. Defaults

See [Configuration Reference](../configuration/reference.md) for full options.

## Agent System

Claude MPM deploys agents from multiple sources. Priority order:

1. **Project**: `.claude-mpm/agents/`
2. **Cached sources**: `~/.claude-mpm/cache/agents/`
3. **User**: `~/.claude-mpm/agents/` (deprecated)
4. **System**: bundled defaults

Common commands:

```bash
claude-mpm agents list
claude-mpm agents list --by-tier
claude-mpm agents deploy
claude-mpm agents create <name>
```

See [Agent Docs](../agents/README.md) and [Single-Tier Agent System](../guides/single-tier-agent-system.md).

## Ticketing Workflows

Claude MPM integrates with ticket systems via `/mpm-ticket`.

```bash
/mpm-ticket organize
/mpm-ticket status
/mpm-ticket update
```

See [Ticketing Workflows](../guides/ticketing-workflows.md).

## Skills System

Skills are Claude Code extensions (not Claude MPM agents). Manage them separately:

- User skills: `~/.claude/skills/`
- Project skills: `.claude/skills/`

See [Skills Guide](skills-guide.md) and [Skills Management](../guides/skills-management.md).

## Memory System

Claude MPM provides resume logs and structured memory for continuity:

- Automatic resume logs at context thresholds
- Optional memory providers (e.g., kuzu-memory)

See [Resume Logs](resume-logs.md) and [Memory System](../reference/MEMORY.md).

## Local Process Management

Run and monitor local dev servers with `local-deploy`:

```bash
claude-mpm local-deploy start --command "npm run dev"
claude-mpm local-deploy list
claude-mpm local-deploy stop <deployment-id>
```

See [Deployment Overview](../deployment/overview.md).

## Session Management

Pause/resume sessions to preserve context:

```bash
claude-mpm mpm-init pause
claude-mpm mpm-init resume
```

See [Session Quick Reference](session-quick-reference.md).

## Real-Time Monitoring

Launch the dashboard:

```bash
claude-mpm run --monitor
```

See [Monitoring Guide](../guides/monitoring.md).

## MCP Gateway

Start the MCP gateway to connect external tools:

```bash
claude-mpm mcp
```

See [MCP Gateway](../developer/13-mcp-gateway/README.md).

## Best Practices

- Run `claude-mpm doctor` after installation or upgrades.
- Keep project agents in `.claude-mpm/agents/` and version them with the repo.
- Use auto-configure when adding Claude MPM to an existing project.
- Prefer guides for task-specific workflows (monitoring, skills, ticketing).

## Next Steps

- [Getting Started](../getting-started/README.md)
- [Troubleshooting](troubleshooting.md)
- [FAQ](../guides/FAQ.md)
