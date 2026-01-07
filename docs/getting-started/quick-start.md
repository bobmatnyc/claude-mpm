# Quick Start

Get Claude MPM running in under 5 minutes.

## Prerequisites

- **Python 3.11+**: `python --version`
- **Claude Code CLI v1.0.92+**: `claude --version`
  - Install: https://docs.anthropic.com/en/docs/claude-code

## Install

```bash
# Recommended (isolated environment)
pipx install "claude-mpm[monitor]"

# Alternative
pip install "claude-mpm[monitor]"
```

## First Run

```bash
# Start a session
claude-mpm

# Or with dashboard
claude-mpm run --monitor
```

## Try a Task

In the Claude session, ask for a task such as:

```
"Analyze this project structure"
"Create tests for this function"
"Help me improve this code"
```

## Essential Commands

| Command | Purpose |
| --- | --- |
| `claude-mpm auto-configure` | Detect stack and deploy agents |
| `claude-mpm doctor` | Run diagnostics |
| `claude-mpm agents list` | List available agents |
| `claude-mpm run --monitor` | Open monitoring dashboard |

## Next Steps

- **Auto-Configuration**: [auto-configuration.md](auto-configuration.md)
- **User Guide**: [../user/user-guide.md](../user/user-guide.md)
- **Troubleshooting**: [../user/troubleshooting.md](../user/troubleshooting.md)
