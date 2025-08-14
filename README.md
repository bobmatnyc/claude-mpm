# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for Claude Code that enables multi-agent workflows, session management, and real-time monitoring through an intuitive interface.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: Automatically delegates tasks to specialized agents (PM, Research, Engineer, QA, Documentation, Security, Ops, Data Engineer, Test Integration, Version Control)
- 🧠 **Agent Memory System**: Persistent learning with project-specific knowledge retention
- 🔄 **Session Management**: Resume previous sessions with `--resume` 
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 📁 **Multi-Project Support**: Per-session working directories
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists

## Installation

```bash
# Basic installation - pure Python, no compilation required
pip install claude-mpm

# Install with development dependencies
pip install "claude-mpm[dev]"

# Install with agent dependencies - pure Python tools
pip install "claude-mpm[agents]"

# Install with all optional dependencies
pip install "claude-mpm[agents,dev]"
```

All dependencies are pure Python - no Rust or compilation required. The `agents` dependency group includes tools for testing, code analysis, documentation, and development workflows.

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

### Agent Management

```bash
# View agent hierarchy and precedence
claude-mpm agents list --by-tier

# Inspect specific agent configuration
claude-mpm agents view engineer

# Fix agent configuration issues
claude-mpm agents fix --all --dry-run
```

For detailed usage, see [QUICKSTART.md](QUICKSTART.md)

### Agent Dependencies

Claude MPM automatically manages Python dependencies required by agents. All dependencies are pure Python packages that don't require compilation. Agents can declare their dependencies in their configuration files, and the system aggregates them for easy installation.

```bash
# Install all agent dependencies (pure Python)
pip install "claude-mpm[agents]"

# View current agent dependencies
python scripts/aggregate_agent_dependencies.py --dry-run

# Update pyproject.toml with latest agent dependencies
python scripts/aggregate_agent_dependencies.py
```

**Agent developers** can declare dependencies in their agent configurations:

```json
{
  "agent_id": "my_agent",
  "dependencies": {
    "python": ["pandas>=2.0.0", "numpy>=1.24.0"],
    "system": ["ripgrep", "git"]
  }
}
```

Dependencies are automatically aggregated from all agent sources (PROJECT > USER > SYSTEM) during the build process, with intelligent version conflict resolution taking the highest compatible version.

For comprehensive documentation, see [docs/AGENT_DEPENDENCIES.md](docs/AGENT_DEPENDENCIES.md).

## Architecture

Claude MPM v3.7.8+ features a **modern service-oriented architecture** with:

### Service Layer Organization
- **Core Services**: Foundation interfaces and dependency injection
- **Agent Services**: Agent lifecycle, deployment, and management
- **Communication Services**: Real-time WebSocket and SocketIO
- **Project Services**: Project analysis and workspace management
- **Infrastructure Services**: Logging, monitoring, and error handling

### Key Architectural Features
- **Interface-Based Design**: All services implement well-defined contracts
- **Dependency Injection**: Loose coupling through service container
- **Lazy Loading**: Performance optimization with deferred initialization
- **Multi-Level Caching**: Intelligent caching with TTL and invalidation
- **Security Framework**: Input validation, path sanitization, and secure operations

For detailed architecture information, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Key Capabilities

### Multi-Agent Orchestration
The PM agent automatically delegates work to specialized agents:
- **Research**: Codebase analysis and investigation
- **Engineer**: Implementation and coding
- **QA**: Testing and validation
- **Documentation**: Docs and guides
- **Security**: Security analysis
- **Ops**: Deployment and infrastructure
- **Data Engineer**: Data pipelines and AI integrations
- **Test Integration**: E2E testing and cross-system validation
- **Version Control**: Git workflows and release management

**Three-Tier Agent System**: PROJECT > USER > SYSTEM precedence allows project-specific agent customization while maintaining fallbacks. Use `claude-mpm agents list --by-tier` to see the active agent hierarchy.

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

# Start with monitoring dashboard
claude-mpm run --monitor
```

See [docs/MEMORY.md](docs/MEMORY.md) for comprehensive memory system documentation.

### Real-Time Monitoring
The `--monitor` flag opens a web dashboard showing:
- Live agent activity and delegations
- File operations with git diff viewer
- Tool usage and results
- Session management UI

See [docs/developer/11-dashboard/README.md](docs/developer/11-dashboard/README.md) for full monitoring guide.


## Documentation

### User Documentation
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Agent Memory System](docs/MEMORY.md)** - Comprehensive memory documentation
- **[Monitoring Dashboard](docs/developer/11-dashboard/README.md)** - Real-time monitoring features
- **[User Guide](docs/user/)** - Detailed usage documentation

### Developer Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - Service-oriented architecture and design
- **[Service Layer Guide](docs/developer/SERVICES.md)** - Service interfaces and implementations
- **[Performance Guide](docs/PERFORMANCE.md)** - Optimization and caching strategies
- **[Security Guide](docs/SECURITY.md)** - Security framework and best practices
- **[Testing Guide](docs/TESTING.md)** - Testing patterns and strategies
- **[Migration Guide](docs/MIGRATION.md)** - Upgrading from previous versions
- **[Project Structure](docs/STRUCTURE.md)** - Codebase organization
- **[Deployment Guide](docs/DEPLOY.md)** - Publishing and versioning
- **[Developer Guide](docs/developer/)** - API reference and internals

## Recent Updates (v3.7.8)

### TSK-0053: Service Layer Architecture Refactoring
- **Service-Oriented Architecture**: Complete redesign with five service domains
- **Interface-Based Contracts**: All services implement explicit interfaces
- **Dependency Injection System**: Service container with automatic dependency resolution
- **Performance Optimizations**: Lazy loading, multi-level caching, connection pooling
- **Security Framework**: Input validation, path traversal prevention, secure operations
- **Backward Compatibility**: Lazy imports maintain existing import paths

### Key Improvements
- **50-80% Performance Improvement**: Optimized caching and lazy loading
- **Enhanced Security**: Comprehensive input validation and sanitization
- **Better Testability**: Interface-based architecture enables easy mocking
- **Improved Maintainability**: Clear separation of concerns and service boundaries
- **Developer Experience**: Rich documentation and migration guides

### Architecture Benefits
- **Scalability**: Service-oriented design supports future growth
- **Extensibility**: Plugin architecture through interfaces and hooks
- **Reliability**: Comprehensive testing with 85%+ coverage
- **Security**: Defense-in-depth security architecture
- **Performance**: Intelligent caching and resource optimization

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
