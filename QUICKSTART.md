# 5-Minute Quick Start

Get Claude MPM running in 5 minutes or less!

> **⚠️ Important**: Claude MPM extends **Claude Code (CLI)**, not Claude Desktop (app). Ensure you have Claude Code CLI installed from https://claude.ai/code

## 1. Install (30 seconds)

**Recommended: pipx with monitor support**
```bash
# Install with full monitor dashboard functionality
pipx install "claude-mpm[monitor]"

# Or install specific version
pipx install "claude-mpm[monitor]==4.3.4"
```

**Alternative: pip installation**
```bash
# New installation
pip install claude-mpm

# Install specific version
pip install claude-mpm==4.3.4

# Upgrade existing installation
pip install --upgrade claude-mpm
```

**Requirements**: Python 3.8+, Claude Code (CLI)

**Why `[monitor]`?** Enables the real-time dashboard that shows agent collaboration in action. Without it, monitoring features won't work!

## 2. Start Claude MPM (10 seconds)

```bash
# Interactive mode (recommended for first time)
claude-mpm
```

This opens a Claude session with multi-agent orchestration enabled.

## 3. Try Your First Task (2 minutes)

Type any of these commands:

```bash
# In interactive mode:
"Analyze this project structure"
"Help me improve this code"
"Create tests for this function"
```

Watch as specialized agents (Research, Engineer, QA) work together!

## 4. Claude Code Slash Commands (2 minutes)

Claude MPM adds powerful slash commands to your Claude Code sessions:

```bash
# Project diagnostics and health check
/mpm-doctor

# Initialize project for Claude MPM (run once per project)
/mpm-init

# Manage and deploy agents
/mpm-agents
```

**Use these commands inside any Claude Code session** - they'll work automatically when Claude MPM is installed.

### Monitor Real-Time Activity
```bash
claude-mpm run --monitor
```
Opens dashboard at http://localhost:8765 showing agent activity.

## What Just Happened?

✅ **Multi-Agent Orchestration**: PM agent automatically delegates to specialists:
   Research → Engineer → QA → Documentation

✅ **Smart MCP Services**: kuzu-memory included, mcp-vector-search auto-installs on first use
   - Interactive prompt offers pip/pipx installation or fallback to grep/glob
   - Your choice is remembered for seamless future use

✅ **Persistent Knowledge**: Project-specific memory graph tracks learnings across sessions

✅ **Session Persistence**: Everything saved, resume anytime

✅ **Intelligent Context**: Prompts automatically enriched with relevant memories

✅ **Real-Time Monitoring**: See agent collaboration live

## First-Use: Vector Search Auto-Install

When you first use semantic search features (e.g., `/mpm-search` or Research agent), you'll see:

```
⚠️  mcp-vector-search not found
This package enables semantic code search (optional feature).

Installation options:
  1. Install via pip (recommended for this project)
  2. Install via pipx (isolated, system-wide)
  3. Skip (use traditional grep/glob instead)

Choose option (1/2/3) [3]:
```

**What to Choose?**
- **Option 1 (pip)**: Installs in your current Python environment. Best for project-specific work.
- **Option 2 (pipx)**: Creates isolated environment. Best if you want vector search globally.
- **Option 3 (skip)**: System continues with grep/glob. You can always install later.

**After Installation**: Vector search works seamlessly. No more prompts!

## Essential Commands

```bash
# Interactive (recommended)
claude-mpm

# With monitoring dashboard
claude-mpm run --monitor

# Semantic code search (triggers auto-install prompt if needed)
claude-mpm search "authentication logic"
/mpm-search "database connection"

# One-time task
claude-mpm run -i "your task" --non-interactive

# Resume previous session
/resume
```

## 🎯 You're Ready!

That's it! You now have:
- Multi-agent task delegation with streamlined Rich interface
- Interactive auto-install for mcp-vector-search (choose pip/pipx on first use)
- Project-specific knowledge graphs for persistent learning (kuzu-memory included)
- Intelligent context enrichment across conversations
- Persistent sessions
- Real-time monitoring

### Quick Tips
- First search triggers interactive mcp-vector-search install (optional)
- Choose option 1 (pip) for quick setup, option 3 (skip) to use grep/glob
- Use `--monitor` for complex tasks to see agent collaboration
- Run `/mpm-init` in new projects to set up Claude MPM
- Use `/mpm-doctor` to troubleshoot issues
- Resume sessions with `/resume` command

## Next Steps

**New Users**:
- [Basic Usage Guide](docs/user/02-guides/basic-usage.md) - Essential commands and workflows

**Full Documentation**:
- [📚 Complete Documentation Hub](docs/README.md) - Master navigation center
- [📦 Installation Guide](docs/user/installation.md) - Advanced installation options
- [🐛 Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and solutions

## Need Help?

**Common Issues**:
- **"Agent not found"**: Run `/mpm-doctor` to diagnose and fix
- **Dashboard won't load**: Check if you installed with `[monitor]`: `pipx install "claude-mpm[monitor]"`
- **Monitor not working**: Run dependency checker: `claude-mpm doctor --checks monitor`
- **Setup issues**: Run `/mpm-init` to initialize project

**Get Support**:
- [🐛 Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [🐛 GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- [📚 Full Documentation](docs/README.md)