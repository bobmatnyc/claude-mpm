# 5-Minute Quick Start

Get Claude MPM running in 5 minutes or less!

## 1. Install (30 seconds)

```bash
# Quick install
pip install claude-mpm
```

**Requirements**: Python 3.8+, Claude Code (for Claude Desktop integration)

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

## 4. Advanced Features (2 minutes)

### Monitor Real-Time Activity
```bash
claude-mpm run --monitor
```
Opens dashboard at http://localhost:8765 showing agent activity.

### Initialize Project Memory
```bash
claude-mpm memory init
```
Agents learn your project patterns and conventions.

### Resume Sessions
```bash
claude-mpm run --resume
```
Continue where you left off.

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

# Resume work
claude-mpm run --resume
```

## 🎯 You're Ready!

That's it! You now have:
- Multi-agent task delegation
- Persistent sessions
- Project-aware agents
- Real-time monitoring

### Quick Tips
- Use `--monitor` for complex tasks to see agent collaboration
- Run `claude-mpm memory init` in new projects
- Agents learn your patterns over time
- Resume sessions with `--resume`

## Next Steps

**New Users**:
- [Basic Usage Guide](docs/user/basic-usage.md) - Essential commands and workflows
- [Memory System](docs/user/memory-system.md) - How agents learn

**Full Documentation**:
- [Complete README](README.md) - All features and capabilities  
- [Installation Guide](docs/user/installation.md) - Advanced installation options
- [Troubleshooting](docs/user/troubleshooting.md) - Common issues and solutions

## Need Help?

**Common Issues**:
- **"Agent not found"**: Run `claude-mpm agents fix --all`
- **Dashboard won't load**: Try `--websocket-port 8766`
- **Session won't resume**: Use full session ID

**Get Support**:
- [Troubleshooting Guide](docs/user/troubleshooting.md)
- [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- [Full Documentation](docs/)