# Quick Start

Get Claude MPM running in under 5 minutes.

## Prerequisites

- **Python 3.11-3.13** (Python 3.13 recommended; 3.14 NOT supported yet)
- **Claude Code CLI v1.0.92+**: `claude --version`
  - Install: https://docs.anthropic.com/en/docs/claude-code

> **macOS Users**: The default Python 3.9 is too old. Use Python 3.13 with the `--python 3.13` flag.

## Complete Installation Sequence

Run these commands from your **home directory** (NOT from within a git repo):

```bash
# Step 1: Go to home directory (IMPORTANT!)
cd ~

# Step 2: Install with Python 3.13
uv tool install claude-mpm[monitor,data-processing] --python 3.13

# Step 3: Install companion tools (recommended)
uv tool install kuzu-memory --python 3.13
uv tool install mcp-browser --python 3.13
uv tool install mcp-ticketer --python 3.13
uv tool install mcp-vector-search --python 3.13

# Step 4: Create required directories
mkdir -p ~/.claude/{responses,memory,logs}

# Step 5: Deploy agents
claude-mpm agents deploy

# Step 6: Add skill source
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills

# Step 7: Verify installation
claude-mpm doctor --verbose

# Step 8: Auto-configure your project
cd ~/your-project
claude-mpm auto-configure
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
| `claude-mpm agents deploy` | Deploy/update agents |

## Common Issues

| Problem | Solution |
| --- | --- |
| Python version too old | Use `--python 3.13` flag with uv |
| Python 3.14 not supported | Downgrade to Python 3.13 |
| Installation conflicts | Install from `~` not from git repo |
| Doctor shows errors | Run post-install setup (Steps 4-6) |

## Next Steps

- **Full Installation Guide**: [installation.md](installation.md)
- **Auto-Configuration**: [auto-configuration.md](auto-configuration.md)
- **User Guide**: [../user/user-guide.md](../user/user-guide.md)
- **Troubleshooting**: [../user/troubleshooting.md](../user/troubleshooting.md)
