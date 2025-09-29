# 👥 Claude MPM User Guide

**Complete user documentation for Claude MPM (Multi-Agent Project Manager)**
**Version 4.4.x** | Last Updated: September 28, 2025

Welcome to Claude MPM! This comprehensive guide covers everything you need to know to use Claude MPM effectively, from installation to advanced features.

## 🎯 What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) is a powerful orchestration framework that extends Claude Code with:

- **🤖 15+ Specialized Agents** - Automatic task delegation to experts (Engineer, QA, Documentation, Security, etc.)
- **🧠 Agent Memory System** - Persistent learning with project-specific knowledge
- **🔄 Session Management** - Resume previous sessions with full context
- **📊 Real-Time Monitoring** - Live dashboard showing agent collaboration
- **🔌 MCP Gateway** - Model Context Protocol integration for extensible tools
- **⚡ Performance** - 50-80% improvement through intelligent caching
- **🔒 Security** - Comprehensive input validation and sanitization

## 🚀 Quick Start (5 Minutes)

### 1. Install (30 seconds)
```bash
# Recommended: Full installation with monitoring
pipx install "claude-mpm[monitor]"

# Alternative: Basic installation
pip install claude-mpm
```

### 2. Start (10 seconds)
```bash
# Interactive mode (recommended)
claude-mpm

# With real-time dashboard
claude-mpm run --monitor
```

### 3. Try Your First Task (2 minutes)
```bash
# In interactive mode, type:
"Analyze this project structure"
"Help me improve this code"
"Create tests for this function"
```

**🎉 That's it!** Watch specialized agents work together automatically.

**💡 Pro Tip**: Use `claude-mpm run --monitor` to see agent collaboration in real-time at http://localhost:8765

## 📖 User Documentation Structure

### 🏁 Getting Started
| Section | Description | When to Use |
|---------|-------------|-------------|
| [🚀 **Quick Start**](quickstart.md) | 5-minute setup guide | First time using Claude MPM |
| [📦 **Installation**](installation.md) | Complete installation options | Need advanced setup options |
| [⚙️ **First Run**](01-getting-started/first-run.md) | Your first Claude MPM session | After installation |
| [🎓 **Core Concepts**](01-getting-started/core-concepts.md) | Understanding the system | Want to understand how it works |

### 📘 How-To Guides
| Guide | Description | Use Case |
|-------|-------------|----------|
| [🎯 **Basic Usage**](02-guides/basic-usage.md) | Essential commands & workflows | Daily usage patterns |
| [🤖 **Agent System**](02-guides/agent-management.md) | Working with agents | Understand agent delegation |
| [💬 **Interactive Mode**](02-guides/interactive-mode.md) | Using the interactive interface | Prefer conversational interface |
| [📊 **Monitoring**](02-guides/monitoring.md) | Real-time dashboard usage | Track agent activity |

### 🔧 Features & Capabilities
| Feature | Description | Documentation |
|---------|-------------|---------------|
| [🧠 **Memory System**](03-features/memory-system.md) | Agent learning & persistence | Agents remembering your patterns |
| [📁 **Session Management**](03-features/session-management.md) | Resume & manage sessions | Working across multiple sessions |
| [🔌 **MCP Gateway**](03-features/mcp-gateway.md) | External tool integration | Extending Claude MPM capabilities |
| [🎛️ **CLI Commands**](03-features/cli-commands.md) | Command-line interface | Scripting & automation |

### 📋 Reference & Support
| Resource | Description | When Needed |
|----------|-------------|-------------|
| [❓ **FAQ**](faq.md) | Frequently asked questions | Quick answers to common questions |
| [🐛 **Troubleshooting**](troubleshooting.md) | Problem diagnosis & solutions | When things don't work |
| [🔄 **Migration Guide**](MIGRATION.md) | Upgrading from previous versions | Updating Claude MPM |
| [⚙️ **Configuration**](04-reference/configuration.md) | Advanced configuration options | Customizing behavior |

## 🎯 Common User Workflows

### 🆕 New User Journey
1. **[Install Claude MPM](installation.md)** → Choose your installation method
2. **[Quick Start](quickstart.md)** → Get running in 5 minutes
3. **[Basic Usage](02-guides/basic-usage.md)** → Learn essential commands
4. **[Agent System](02-guides/agent-management.md)** → Understand agent delegation
5. **[Memory System](03-features/memory-system.md)** → Enable agent learning

### 📝 Daily Usage Patterns
1. **Start Session**: `claude-mpm run` or `claude-mpm run --monitor`
2. **Give Tasks**: Natural language requests → automatic agent delegation
3. **Monitor Progress**: Use dashboard or command line feedback
4. **Resume Work**: `claude-mpm resume` to continue previous sessions
5. **Review Results**: Check generated files, tests, documentation

### 🔧 Advanced Usage
1. **Custom Agents**: Create project-specific agents in `.claude-mpm/agents/`
2. **Memory Management**: Initialize and manage agent memories
3. **MCP Integration**: Connect external tools and services
4. **Session Organization**: Manage multiple projects and sessions
5. **Performance Optimization**: Configure caching and lazy loading

## ✨ Key Features Explained

### 🤖 Multi-Agent System
- **PM Agent**: Orchestrates and delegates tasks
- **15+ Specialists**: Engineer, QA, Documentation, Security, Research, etc.
- **Smart Routing**: Automatic task delegation based on context
- **Collaboration**: Agents work together on complex projects

### 🧠 Memory System
- **Project Learning**: Agents remember your coding patterns
- **Persistent Knowledge**: Knowledge retained across sessions
- **JSON Updates**: Simple `remember` field for incremental learning
- **Initialization**: `claude-mpm memory init` to set up learning

### 📊 Real-Time Monitoring
- **Live Dashboard**: http://localhost:8765 with `--monitor` flag
- **Agent Activity**: See which agents are working on what
- **File Operations**: Track file changes in real-time
- **Session Management**: Visual session state and progress

### 🔄 Session Management
- **Persistent Sessions**: All work saved automatically
- **Resume Capability**: `claude-mpm resume` to continue
- **Multi-Project**: Different sessions for different projects
- **History Tracking**: Complete audit trail of all activities

## 🆘 Getting Help

### Quick Troubleshooting
| Problem | Solution | Documentation |
|---------|----------|---------------|
| **Installation issues** | Run `claude-mpm doctor` | [Installation Guide](installation.md) |
| **Agent not found** | Check agent deployment with `/mpm-agents` | [Agent Management](02-guides/agent-management.md) |
| **Dashboard won't load** | Install with `[monitor]`: `pipx install "claude-mpm[monitor]"` | [Monitoring Guide](02-guides/monitoring.md) |
| **Memory not working** | Initialize with `claude-mpm memory init` | [Memory System](03-features/memory-system.md) |

### Support Resources
1. **📖 [Troubleshooting Guide](troubleshooting.md)** - Comprehensive problem-solving
2. **❓ [FAQ](faq.md)** - Quick answers to common questions
3. **🐛 [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)** - Report bugs and get help
4. **📚 [Full Documentation](../README.md)** - Complete navigation hub

## 🤝 Related Documentation

- **📚 [Documentation Hub](../README.md)** - Master navigation center
- **💻 [Developer Guide](../developer/README.md)** - For contributing and extending
- **🤖 [Agent System](../AGENTS.md)** - Creating custom agents
- **🚀 [Deployment](../DEPLOYMENT.md)** - Operations and release management
- **📊 [Architecture](../developer/ARCHITECTURE.md)** - Understanding the system design

## 🔄 Version Information

**Current Version**: 4.3.3
**Documentation Updated**: September 19, 2025

### Recent Improvements (v4.3.x)
- ✅ Enhanced PM instructions with PM2 deployment support
- ✅ Mandatory web-qa verification for quality assurance
- ✅ Improved version comparison logic and agent override warnings
- ✅ Auto-fix code formatting and import management
- ✅ Standard tools recognition for better integration

See [Migration Guide](MIGRATION.md) for upgrade instructions and [CHANGELOG.md](../../CHANGELOG.md) for complete version history.

---

**💡 Quick Tip**: New to Claude MPM? Start with the [Quick Start Guide](quickstart.md) - you'll be productive in 5 minutes! For deeper understanding, explore the guides and features sections above.