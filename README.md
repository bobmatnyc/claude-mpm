# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for Claude Code that enables multi-agent workflows, session management, and real-time monitoring through an intuitive interface.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: 15 specialized agents for comprehensive project management
- 🧠 **Agent Memory System**: Simple list-based persistent learning with JSON response field updates
- 🔄 **Session Management**: Resume previous sessions with `--resume` 
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 🔌 **MCP Gateway**: Model Context Protocol integration for extensible tool capabilities
- 📁 **Multi-Project Support**: Per-session working directories
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists
- ⚡ **50-80% Performance Improvement**: Through intelligent caching and lazy loading
- 🔒 **Enhanced Security**: Comprehensive input validation and sanitization framework

## Quick Installation

```bash
pip install claude-mpm
```

Or with pipx (recommended for isolated installation):
```bash
# Install with monitor support (recommended)
pipx install "claude-mpm[monitor]"

# Basic installation without monitor
pipx install claude-mpm

# Configure MCP for pipx users:
claude-mpm mcp-pipx-config
```

**💡 Pipx Tip**: Use `"claude-mpm[monitor]"` to get full monitoring dashboard functionality! The `[monitor]` optional dependency includes Socket.IO and async web server components needed for real-time agent monitoring.

**🎉 Pipx Support Now Fully Functional!** Recent improvements ensure complete compatibility:
- ✅ Socket.IO daemon script path resolution (fixed)
- ✅ Commands directory access (fixed) 
- ✅ Resource files properly packaged for pipx environments
- ✅ Python 3.13+ fully supported

**That's it!** See [QUICKSTART.md](QUICKSTART.md) for immediate usage or [docs/user/installation.md](docs/user/installation.md) for advanced options.

## Quick Usage

```bash
# Start interactive mode (recommended)
claude-mpm

# Start with monitoring dashboard
claude-mpm run --monitor

# Use MCP Gateway for external tool integration
claude-mpm mcp

# Run health diagnostics  
claude-mpm doctor

# Manage memory for large conversation histories
claude-mpm cleanup-memory
```

See [QUICKSTART.md](QUICKSTART.md) for complete usage examples.


## Architecture (v4.1.0+)

Following continuous improvements through v4.1.0, Claude MPM features:

- **Service-Oriented Architecture**: Five specialized service domains with Socket.IO stability improvements
- **Interface-Based Contracts**: All services implement explicit interfaces
- **Dependency Injection**: Service container with automatic resolution
- **50-80% Performance Improvement**: Through lazy loading and intelligent caching
- **Enhanced Security**: Comprehensive input validation and sanitization framework
- **Improved Monitoring**: Enhanced dashboard with hierarchical agent display
- **Socket.IO Stability**: Major reliability improvements for real-time communication

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed architecture information.

## Key Capabilities

### Multi-Agent Orchestration

Claude MPM includes 15 specialized agents:

#### Core Development
- **Engineer** - Software development and implementation
- **Research** - Code analysis and research  
- **Documentation** - Documentation creation and maintenance
- **QA** - Testing and quality assurance
- **Security** - Security analysis and implementation

#### Operations & Infrastructure
- **Ops** - Operations and deployment with advanced git commit authority and security verification (v2.2.2+)
- **Version Control** - Git and version management
- **Data Engineer** - Data pipeline and ETL development

#### Web Development
- **Web UI** - Frontend and UI development
- **Web QA** - Web testing and E2E validation

#### Project Management
- **Ticketing** - Issue tracking and management
- **Project Organizer** - File organization and structure
- **Memory Manager** - Project memory and context management

#### Code Quality
- **Refactoring Engineer** - Code refactoring and optimization
- **Code Analyzer** - Static code analysis with AST and tree-sitter

### Agent Memory System
Agents learn project-specific patterns using a simple list format and can update memories via JSON response fields (`remember` for incremental updates, `MEMORIES` for complete replacement). Initialize with `claude-mpm memory init`.

### MCP Gateway (Model Context Protocol)

Claude MPM includes a powerful MCP Gateway that enables:
- Integration with external tools and services
- Custom tool development
- Protocol-based communication
- Extensible architecture

See [MCP Gateway Documentation](docs/developer/13-mcp-gateway/README.md) for details.

### Memory Management

Large conversation histories can consume 2GB+ of memory. Use the `cleanup-memory` command to manage Claude conversation history:

```bash
# Clean up old conversation history
claude-mpm cleanup-memory

# Keep only recent conversations
claude-mpm cleanup-memory --days 7
```

### Real-Time Monitoring
The `--monitor` flag opens a web dashboard showing live agent activity, file operations, and session management.

See [docs/MEMORY.md](docs/MEMORY.md) and [docs/developer/11-dashboard/README.md](docs/developer/11-dashboard/README.md) for details.


## Documentation

### User Documentation
- **[Quick Start Guide](QUICKSTART.md)** - Get running in 5 minutes
- **[Installation Guide](docs/user/installation.md)** - Complete installation options
- **[User Guide](docs/user/)** - Detailed usage documentation
- **[Memory System](docs/MEMORY.md)** - Agent memory documentation
- **[Troubleshooting](docs/user/troubleshooting.md)** - Common issues and solutions

### Developer Documentation
- **[Architecture Overview](docs/ARCHITECTURE.md)** - Service-oriented architecture and design
- **[API Reference](docs/api/)** - Complete API documentation with Sphinx
- **[Service Layer Guide](docs/developer/SERVICES.md)** - Service interfaces and implementations
- **[MCP Gateway Guide](docs/developer/13-mcp-gateway/README.md)** - Model Context Protocol integration
- **[Performance Guide](docs/PERFORMANCE.md)** - Optimization and caching strategies
- **[Security Guide](docs/SECURITY.md)** - Security framework and best practices
- **[Testing Guide](docs/TESTING.md)** - Testing patterns and strategies
- **[Migration Guide](docs/MIGRATION.md)** - Upgrading from previous versions
- **[Developer Guide](docs/developer/)** - Comprehensive development documentation

### API Documentation
Comprehensive API documentation is available at [docs/api/](docs/api/) - build with `make html` in that directory.

## Recent Updates (v4.1.0)

**Socket.IO Stability Improvements**: Major reliability enhancements for real-time communication with improved error handling and connection management.

**Project Organization**: Comprehensive cleanup and reorganization with structured script directories for better maintainability.

**Documentation Consolidation**: Streamlined documentation structure with consolidated guides and improved navigation.

**Agent Hierarchy Display**: Enhanced dashboard with hierarchical agent display showing PM at top level with visual distinction for implied vs explicit nodes.

See [CHANGELOG.md](CHANGELOG.md) for full history and [docs/MIGRATION.md](docs/MIGRATION.md) for upgrade instructions.

## Development

### Quick Development Setup
```bash
# Complete development setup with code formatting and quality tools
make dev-complete

# Or step by step:
make setup-dev          # Install in development mode
make setup-pre-commit    # Set up automated code formatting
```

### Code Quality & Formatting
The project uses automated code formatting and quality checks:
- **Black** for code formatting
- **isort** for import sorting
- **flake8** for linting
- **mypy** for type checking
- **Pre-commit hooks** for automatic enforcement

See [docs/developer/CODE_FORMATTING.md](docs/developer/CODE_FORMATTING.md) for details.

### Contributing
Contributions are welcome! Please see our [project structure guide](docs/STRUCTURE.md) and follow the established patterns.

**Development Workflow**:
1. Run `make dev-complete` to set up your environment
2. Code formatting happens automatically on commit
3. All code must pass quality checks before merging

### Project Structure
See [docs/STRUCTURE.md](docs/STRUCTURE.md) for codebase organization.

### License
MIT License - see [LICENSE](LICENSE) file.

## Credits

- Based on [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm)
- Enhanced for [Claude Code](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
