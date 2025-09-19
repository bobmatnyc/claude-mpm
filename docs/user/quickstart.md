# 🚀 Claude MPM Quick Start Guide

**Get Claude MPM running in 5 minutes!**
**Version 4.3.4** | For immediate productivity

## ⚡ Quick Setup (5 Minutes Total)

### 1. Install (30 seconds)

**✅ Recommended: Full Installation with Monitor**
```bash
# Install with real-time dashboard functionality
pipx install "claude-mpm[monitor]"

# Or install specific version
pipx install "claude-mpm[monitor]==4.3.4"
```

**📦 Alternative: pip Installation**
```bash
# New installation
pip install claude-mpm

# Install specific version
pip install claude-mpm==4.3.4

# Upgrade existing installation
pip install --upgrade claude-mpm
```

**📋 Requirements**: Python 3.8+, Claude Code

**💡 Why `[monitor]`?** Enables the real-time dashboard that shows agent collaboration in action. Essential for complex projects!

### 2. Start Claude MPM (10 seconds)

```bash
# Interactive mode (recommended for first time)
claude-mpm

# With real-time monitoring dashboard
claude-mpm run --monitor
```

**🎯 What happens**: Opens a Claude Code session with 15+ specialized agents ready to help.

### 3. Try Your First Task (2 minutes)

In the Claude session, try any of these:

```bash
# Project analysis
"Analyze this project structure and suggest improvements"

# Code improvement
"Help me refactor this function for better performance"

# Quality assurance
"Create comprehensive tests for this module"

# Documentation
"Generate documentation for this API"
```

**🤖 Watch the Magic**: PM agent automatically delegates to specialists (Research → Engineer → QA → Documentation)

### 4. Explore Claude Code Slash Commands (2 minutes)

Claude MPM adds powerful slash commands to Claude Code:

```bash
# Project health check and diagnostics
/mpm-doctor

# Initialize project for Claude MPM (run once per project)
/mpm-init

# Manage and deploy custom agents
/mpm-agents

# Resume previous session
/mpm-resume
```

**💡 Pro Tip**: These commands work in any Claude Code session once Claude MPM is installed!

## 🎯 What Just Happened?

### ✅ Multi-Agent Orchestration
- **PM Agent** automatically routes tasks to specialists
- **15+ Expert Agents**: Engineer, QA, Documentation, Security, Research, etc.
- **Smart Collaboration**: Agents work together on complex projects

### ✅ Session Persistence
- Everything automatically saved
- Resume anytime with full context
- Multi-project support

### ✅ Project Learning
- Agents remember your coding patterns
- Persistent knowledge across sessions
- Automatic pattern recognition

### ✅ Real-Time Monitoring
- Live dashboard at http://localhost:8765 (with `--monitor`)
- See agent activity in real-time
- Track file operations and progress

## 🛠️ Essential Commands

### Daily Usage
```bash
# Start interactive session
claude-mpm

# Start with monitoring dashboard
claude-mpm run --monitor

# One-time task
claude-mpm run -i "your task" --non-interactive

# Resume previous session
claude-mpm resume
```

### Project Management
```bash
# Health check and diagnostics
claude-mpm doctor

# Initialize project memory
claude-mpm memory init

# List available agents
claude-mpm agents list

# Clean up old conversation history
claude-mpm cleanup-memory
```

### MCP Gateway (Advanced)
```bash
# Start MCP Gateway for external tools
claude-mpm mcp

# Configure MCP for pipx installations
claude-mpm mcp-pipx-config
```

## 🎉 You're Ready!

### What You Now Have:
- ✅ **Multi-agent task delegation** - Automatic expert routing
- ✅ **Persistent sessions** - Never lose context
- ✅ **Project-aware agents** - Remember your patterns
- ✅ **Real-time monitoring** - See collaboration in action
- ✅ **Quality workflows** - Automatic testing and validation

### Quick Success Tips:
1. **Use `--monitor`** for complex tasks to see agent collaboration
2. **Run `/mpm-init`** in new projects to set up Claude MPM
3. **Use `/mpm-doctor`** to troubleshoot any issues
4. **Resume sessions** with `/mpm-resume` to continue work
5. **Be specific** in requests for better agent delegation

## 🎯 Next Steps by Experience Level

### 🆕 New Users
- [📖 **User Guide**](README.md) - Complete user documentation
- [🎯 **Basic Usage**](02-guides/basic-usage.md) - Essential commands and workflows
- [🤖 **Agent System**](02-guides/agent-management.md) - Understanding agent delegation

### 👨‍💻 Developers
- [🏗️ **Architecture**](../developer/ARCHITECTURE.md) - Service-oriented system design
- [💻 **Development**](../developer/README.md) - Contributing and extending
- [🔧 **API Reference**](../API.md) - Service interfaces and APIs

### 🔧 Advanced Users
- [🧠 **Memory System**](03-features/memory-system.md) - Agent learning configuration
- [🔌 **MCP Gateway**](03-features/mcp-gateway.md) - External tool integration
- [📊 **Monitoring**](02-guides/monitoring.md) - Dashboard configuration

## 🆘 Need Help?

### Common First-Time Issues:

| Problem | Quick Fix | Documentation |
|---------|-----------|---------------|
| **"Agent not found"** | Run `/mpm-doctor` to diagnose | [Troubleshooting](troubleshooting.md) |
| **Dashboard won't load** | Reinstall: `pipx install "claude-mpm[monitor]"` | [Installation](installation.md) |
| **Monitor not working** | Check dependencies: `python scripts/check_monitor_deps.py` | [Monitoring Guide](02-guides/monitoring.md) |
| **Setup issues** | Initialize project: `/mpm-init` | [First Run](01-getting-started/first-run.md) |

### Get Support:
- **📖 [Troubleshooting Guide](troubleshooting.md)** - Comprehensive solutions
- **❓ [FAQ](faq.md)** - Quick answers to common questions
- **🐛 [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)** - Report problems
- **📚 [Complete Documentation](../README.md)** - Full feature guide

## 🔄 What's Next?

### Immediate Actions:
1. **Try complex tasks** - See multi-agent collaboration in action
2. **Explore the dashboard** - Use `--monitor` to visualize agent work
3. **Set up project memory** - Run `claude-mpm memory init` for learning
4. **Create custom agents** - Project-specific expertise in `.claude-mpm/agents/`

### Learning Path:
1. **Master basics** → [Basic Usage Guide](02-guides/basic-usage.md)
2. **Understand agents** → [Agent Management](02-guides/agent-management.md)
3. **Configure features** → [Memory System](03-features/memory-system.md)
4. **Advanced integration** → [MCP Gateway](03-features/mcp-gateway.md)

---

**🎯 Success Indicator**: If you can run `claude-mpm run --monitor` and see the dashboard at http://localhost:8765, you're fully set up! Now you have a powerful multi-agent development environment at your fingertips.

**💡 Quick Tip**: The more specific your requests, the better Claude MPM can route them to the right specialist agents. Try "Create unit tests with pytest for the authentication module" instead of just "create tests"!