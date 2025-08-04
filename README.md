# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for Claude Code that enables multi-agent workflows, session management, and real-time monitoring through an intuitive interface.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: Automatically delegates tasks to specialized agents (PM, Research, Engineer, QA, Documentation, Security, Ops, Data Engineer)
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

### Real-Time Monitoring
The `--monitor` flag opens a web dashboard showing:
- Live agent activity and delegations
- File operations with git diff viewer
- Tool usage and results
- Session management UI

See [docs/monitoring.md](docs/monitoring.md) for full monitoring guide.


## Documentation

- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Monitoring Dashboard](docs/monitoring.md)** - Real-time monitoring features
- **[Project Structure](docs/STRUCTURE.md)** - Codebase organization
- **[Deployment Guide](docs/DEPLOY.md)** - Publishing and versioning
- **[User Guide](docs/user/)** - Detailed usage documentation
- **[Developer Guide](docs/developer/)** - Architecture and API reference

## Recent Updates (v3.3.1)

### Session Working Directories
- Each session can now have its own working directory
- Git operations use the session's directory automatically
- Switch projects seamlessly without changing terminal directory

### Monitoring Improvements
- Fixed git diff viewer for cross-project files
- Auto-sync working directory from session data
- Improved error handling and display

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
