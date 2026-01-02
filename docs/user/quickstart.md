---
title: 5-Minute Quick Start
version: 5.4.71
last_updated: 2026-01-02
status: current
---

# 5-Minute Quick Start

Get Claude MPM running in under 5 minutes.

## Prerequisites

- **Python 3.11+** — Check: `python --version`
- **Claude Code CLI** (v1.0.92+) — Install: https://docs.anthropic.com/en/docs/claude-code
- **pipx** (optional, but recommended) — Install: `python -m pip install --user pipx`

## Installation

### Option 1: pipx (Recommended)
```bash
pipx install "claude-mpm[monitor]"
```

### Option 2: pip
```bash
pip install "claude-mpm[monitor]"
```

### Verify Installation
```bash
claude-mpm --version
claude --version  # Should be v1.0.92 or higher
```

## First Run

### Start Claude MPM
```bash
claude-mpm
```

This launches Claude with multi-agent orchestration enabled.

### Try a Task
In the Claude session, type any development task:
```
"Analyze this project structure"
"Help me improve this code"
"Create tests for this function"
"Fix this bug"
```

Watch specialized agents (Research, Engineer, QA) collaborate automatically!

## Essential Commands

| Command | Description |
|---------|-------------|
| `claude-mpm` | Start interactive session with agents |
| `claude-mpm run --monitor` | Start with real-time dashboard |
| `claude-mpm auto-configure` | Auto-detect your project stack |
| `claude-mpm agents list` | See available agents |
| `claude-mpm doctor` | Run diagnostics |

## What's Next?

- **Full Features**: [User Guide](user-guide.md)
- **Auto-Configuration**: `claude-mpm auto-configure` (detect your stack automatically)
- **With Dashboard**: `claude-mpm run --monitor` (see agents working in real-time)
- **Help**: [Troubleshooting](troubleshooting.md) or `claude-mpm doctor`

---

You're ready! Just run `claude-mpm` in your project directory.
