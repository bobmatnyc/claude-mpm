# Frequently Asked Questions

## Basics

### What is Claude MPM?

Claude MPM extends Claude Code CLI with multi-agent workflows, session management, and monitoring.

### Do I need Claude Desktop or Claude Code?

You need **Claude Code CLI** (v1.0.92+). Claude Desktop is not supported.

Install: https://docs.anthropic.com/en/docs/claude-code

## Installation

### How do I install Claude MPM?

```bash
pipx install "claude-mpm[monitor]"
claude-mpm --version
claude-mpm doctor
```

See [Installation](../getting-started/installation.md).

### pip vs pipx?

Use **pipx** unless you already manage a virtualenv. It avoids dependency conflicts.

### Optional dependencies?

- `[monitor]` for the dashboard
- `kuzu-memory` for advanced memory
- `mcp-vector-search` for semantic search

## Usage

### How do I start a session?

```bash
claude-mpm
# or with dashboard
claude-mpm run --monitor
```

See [Quick Start](../getting-started/quick-start.md).

### How do I auto-configure agents?

```bash
claude-mpm auto-configure
```

See [Auto-Configuration](../getting-started/auto-configuration.md).

### How do I use the monitoring dashboard?

```bash
claude-mpm run --monitor
```

See [Monitoring](../guides/monitoring.md).

## Agents and Skills

### What is the agent priority order?

Project > Cached sources > User (deprecated) > System.

See [Agent System](../agents/README.md) and [Single-Tier Agent System](../guides/single-tier-agent-system.md).

### Where do skills live?

Skills are Claude Code features:

- User: `~/.claude/skills/`
- Project: `.claude/skills/`

See [Skills Guide](../user/skills-guide.md).

## Configuration

### Where are config files stored?

- Project: `.claude-mpm/config.yaml`
- User: `~/.claude-mpm/config.yaml`

See [Configuration Reference](../configuration/reference.md).

## Resume Logs

### What are resume logs?

Structured summaries created near context limits to continue work in a new session.

See [Resume Logs](../user/resume-logs.md).

## Troubleshooting

### Claude MPM won't start

```bash
claude-mpm doctor
```

See [Troubleshooting](../user/troubleshooting.md).
