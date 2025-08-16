# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for Claude Code that enables multi-agent workflows, session management, and real-time monitoring through an intuitive interface.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: Automatically delegates tasks to specialized agents (PM, Research, Engineer, QA, Documentation, Security, Ops, Data Engineer, Test Integration, Version Control)
- 🧠 **Agent Memory System**: Persistent learning with project-specific knowledge retention
- 🔄 **Session Management**: Resume previous sessions with `--resume` 
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 🛡️ **Memory Guardian (Experimental)**: Automatic memory monitoring and intelligent restarts to prevent crashes
- 📁 **Multi-Project Support**: Per-session working directories
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists

## Quick Installation

```bash
pip install claude-mpm
```

**That's it!** See [QUICKSTART.md](QUICKSTART.md) for immediate usage or [docs/user/installation.md](docs/user/installation.md) for advanced options.

## Quick Usage

```bash
# Start interactive mode (recommended)
claude-mpm

# Start with monitoring dashboard
claude-mpm run --monitor

# Start with memory protection (prevents crashes from large conversations)
claude-mpm run-guarded
```

See [QUICKSTART.md](QUICKSTART.md) for complete usage examples.


## Architecture

Claude MPM v3.8.2+ features a **modern service-oriented architecture** with interface-based design, dependency injection, and intelligent caching for 50-80% performance improvements.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture information.

## Key Capabilities

### Multi-Agent Orchestration
The PM agent automatically delegates work to specialized agents including Research, Engineer, QA, Documentation, Security, Ops, Data Engineer, Test Integration, and Version Control.

### Agent Memory System
Agents learn project-specific patterns and remember insights across sessions. Initialize with `claude-mpm memory init`.

### Memory Guardian System (Experimental)
**⚠️ Beta Feature** - Prevents memory-related crashes through intelligent monitoring and automatic restarts with state preservation.

```bash
# Start with memory protection (recommended for long sessions)
claude-mpm run-guarded --accept-experimental

# Custom memory threshold for your system
claude-mpm run-guarded --memory-threshold 16000 --accept-experimental  # 16GB
```

**Why Memory Guardian?** Large conversation histories can consume 2GB+ of memory, causing system instability. The Memory Guardian monitors memory usage and performs controlled restarts while preserving your conversation context and work progress.

**Note:** This is an experimental feature in beta. Use `--accept-experimental` to suppress warnings.

### Real-Time Monitoring
The `--monitor` flag opens a web dashboard showing live agent activity, file operations, and session management.

See [docs/MEMORY.md](docs/MEMORY.md), [docs/USER_GUIDE_MEMORY_GUARDIAN.md](docs/USER_GUIDE_MEMORY_GUARDIAN.md), and [docs/developer/11-dashboard/README.md](docs/developer/11-dashboard/README.md) for details.


## Documentation

### User Documentation
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Installation Guide](docs/user/installation.md)** - Complete installation options
- **[User Guide](docs/user/)** - Detailed usage documentation
- **[Memory System](docs/MEMORY.md)** - Agent memory documentation
- **[Memory Guardian Guide](docs/USER_GUIDE_MEMORY_GUARDIAN.md)** - Comprehensive memory protection documentation
- **[Troubleshooting](docs/user/troubleshooting.md)** - Common issues and solutions

### Developer Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - Service-oriented architecture and design
- **[API Reference](docs/api/)** - Complete API documentation with Sphinx
- **[Service Layer Guide](docs/developer/SERVICES.md)** - Service interfaces and implementations
- **[Memory Guardian Technical](docs/MEMORY_GUARDIAN_TECHNICAL.md)** - Technical architecture and implementation details
- **[Memory Guardian Configuration](docs/MEMORY_GUARDIAN_CONFIG.md)** - Complete configuration reference
- **[Performance Guide](docs/PERFORMANCE.md)** - Optimization and caching strategies
- **[Security Guide](docs/SECURITY.md)** - Security framework and best practices
- **[Testing Guide](docs/TESTING.md)** - Testing patterns and strategies
- **[Migration Guide](docs/MIGRATION.md)** - Upgrading from previous versions
- **[Developer Guide](docs/developer/)** - Comprehensive development documentation

### API Documentation
Comprehensive API documentation is available at [docs/api/](docs/api/) - build with `make html` in that directory.

## Recent Updates (v3.8.2)

**Major Architecture Refactoring (TSK-0053)**: Complete service-oriented redesign with 50-80% performance improvements, enhanced security, and interface-based design.

**Process Management Improvements**: Enhanced hook system reliability with automatic process cleanup, timeout protection, and orphan process monitoring to prevent resource leaks.

See [CHANGELOG.md](CHANGELOG.md) for full history and [docs/MIGRATION.md](docs/MIGRATION.md) for upgrade instructions.

## Development

### Contributing
Contributions are welcome! Please see our [project structure guide](docs/STRUCTURE.md) and follow the established patterns.

### Project Structure
See [docs/STRUCTURE.md](docs/STRUCTURE.md) for codebase organization.

### License
MIT License - see [LICENSE](LICENSE) file.

## Credits

- Based on [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm)
- Enhanced for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
