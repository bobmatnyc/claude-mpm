# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for Claude Code that enables multi-agent workflows, session management, and real-time monitoring through an intuitive interface.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: Automatically delegates tasks to specialized agents (PM, Research, Engineer, QA, Documentation, Security, Ops, Data Engineer)
- 🧠 **Agent Memory System**: Persistent learning with project-specific knowledge retention
- 🔄 **Session Management**: Resume previous sessions with `--resume` 
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 📁 **Multi-Project Support**: Per-session working directories
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists

## Installation

```bash
# Install from PyPI
pip install claude-mpm

# Or with monitoring support
pip install "claude-mpm[monitor]"
```

## Basic Usage

```bash
# Interactive mode (recommended)
claude-mpm

# Non-interactive with task
claude-mpm run -i "analyze this codebase" --non-interactive

# With monitoring dashboard
claude-mpm run --monitor

# Resume last session
claude-mpm run --resume
```

For detailed usage, see [QUICKSTART.md](QUICKSTART.md)

## Key Capabilities

### Multi-Agent Orchestration
The PM agent automatically delegates work to specialized agents:
- **Research**: Codebase analysis and investigation
- **Engineer**: Implementation and coding
- **QA**: Testing and validation
- **Documentation**: Docs and guides
- **Security**: Security analysis
- **Ops**: Deployment and infrastructure

### Session Management
- All work is tracked in persistent sessions
- Resume any session with `--resume`
- Switch between projects with per-session directories
- View session history and activity

### Agent Memory System
Agents learn and improve over time with persistent memory:
- **Project-Specific Knowledge**: Automatically analyzes your codebase to understand patterns
- **Continuous Learning**: Agents remember insights across sessions
- **Memory Management**: Initialize, optimize, and manage agent memories
- **Quick Initialization**: Use `/mpm memory init` to scan project and create memories

```bash
# Initialize project-specific memories
claude-mpm memory init

# View memory status
claude-mpm memory status

# Add specific learning
claude-mpm memory add engineer pattern "Always use async/await for I/O"
```

See [docs/MEMORY.md](docs/MEMORY.md) for comprehensive memory system documentation.

### Real-Time Monitoring
The `--monitor` flag opens a web dashboard showing:
- Live agent activity and delegations
- File operations with git diff viewer
- Tool usage and results
- Session management UI

See [docs/monitoring.md](docs/monitoring.md) for full monitoring guide.


## Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Agent Memory System](docs/MEMORY.md)** - Comprehensive memory documentation
- **[Monitoring Dashboard](docs/monitoring.md)** - Real-time monitoring features
- **[Project Structure](docs/STRUCTURE.md)** - Codebase organization
- **[Deployment Guide](docs/DEPLOY.md)** - Publishing and versioning
- **[User Guide](docs/user/)** - Detailed usage documentation
- **[Developer Guide](docs/developer/)** - Architecture and API reference

## Recent Updates (v3.4.0)

### Agent Memory System
- **Project-Specific Memory Generation**: Automatic analysis of project characteristics
- **Memory Initialization Command**: New `/mpm memory init` for quick project onboarding
- **Enhanced Documentation Processing**: Dynamic file discovery based on project type
- **Improved Memory Templates**: Clean section headers with programmatic limit enforcement

### Project Organization
- **Deep Clean**: Comprehensive project structure cleanup for publishing readiness
- **Documentation Archives**: Historical reports organized in docs/archive/
- **Test Organization**: All tests properly relocated to /tests/ directory
- **Enhanced .gitignore**: Prevents temporary and debug file commits

See [CHANGELOG.md](CHANGELOG.md) for full history.

## Development

### Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Project Structure
See [docs/STRUCTURE.md](docs/STRUCTURE.md) for codebase organization.

### License
MIT License - see [LICENSE](LICENSE) file.

## Credits

- Based on [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm)
- Enhanced for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
