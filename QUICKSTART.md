# 5-Minute Quick Start

Get Claude MPM running in 5 minutes or less!

## 1. Install (30 seconds)

**Recommended: pipx with monitor support**
```bash
# Install with full monitor dashboard functionality
pipx install "claude-mpm[monitor]"
```

**Alternative: pip (requires virtual environment)**
```bash
# Basic installation
pip install claude-mpm
```

**Requirements**: Python 3.8+, Claude Code

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

✅ **Session Persistence**: Everything saved, resume anytime

✅ **Project Learning**: Agents remember your patterns and preferences

✅ **Real-Time Monitoring**: See agent collaboration live

## Essential Commands

```bash
# Interactive (recommended)
claude-mpm

# With monitoring dashboard
claude-mpm run --monitor

# One-time task
claude-mpm run -i "your task" --non-interactive

# Resume previous session
/resume
```

## 🎯 You're Ready!

That's it! You now have:
- Multi-agent task delegation
- Persistent sessions
- Project-aware agents
- Real-time monitoring

### Quick Tips
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
- **Monitor not working**: Run dependency checker: `python scripts/check_monitor_deps.py`
- **Setup issues**: Run `/mpm-init` to initialize project

**Get Support**:
- [🐛 Troubleshooting Guide](docs/TROUBLESHOOTING.md)
- [🐛 GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- [📚 Full Documentation](docs/README.md)