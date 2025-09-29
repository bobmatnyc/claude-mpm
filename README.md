# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for **Claude Code (CLI)** that enables multi-agent workflows, session management, and real-time monitoring through a streamlined Rich-based interface.

> **⚠️ Important**: Claude MPM extends **Claude Code (CLI)**, not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: 15 specialized agents for comprehensive project management
- 🧠 **Persistent Knowledge System**: Project-specific kuzu-memory integration for intelligent context retention
- 🔄 **Session Management**: Resume previous sessions with `--resume`
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 🔌 **Optional MCP Services**: mcp-vector-search and kuzu-memory with automatic fallback installation
- 📁 **Multi-Project Support**: Per-session working directories with persistent knowledge graphs
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists
- ⚡ **Simplified Architecture**: ~3,700 lines removed for better performance and maintainability
- 🔒 **Enhanced Security**: Comprehensive input validation and sanitization framework

## Quick Installation

```bash
# Basic installation
pip install claude-mpm

# Install with optional MCP services (recommended)
pip install "claude-mpm[mcp]"
```

Or with pipx (recommended for isolated installation):
```bash
# Basic installation
pipx install claude-mpm

# Install with optional MCP services (recommended)
pipx install "claude-mpm[mcp]"

# Install with all features
pipx install "claude-mpm[mcp,monitor]"

# Configure MCP for pipx users:
claude-mpm mcp-pipx-config
```

**💡 Optional Dependencies**:
- `[mcp]` - Include MCP services (mcp-vector-search, mcp-browser, mcp-ticketer, kuzu-memory)
- `[monitor]` - Full monitoring dashboard with Socket.IO and async web server components
- **Combine both**: Use `"claude-mpm[mcp,monitor]"` to install all features
- Without optional dependencies, MCP services auto-install on first use via pipx

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

# Run comprehensive health diagnostics
claude-mpm doctor

# Generate detailed diagnostic report with MCP service analysis
claude-mpm doctor --verbose --output-file doctor-report.md

# Run specific diagnostic checks including MCP services
claude-mpm doctor --checks installation configuration agents mcp

# Check MCP service status specifically
claude-mpm doctor --checks mcp --verbose

# Verify MCP services installation and configuration
claude-mpm verify

# Auto-fix MCP service issues
claude-mpm verify --fix

# Verify specific service
claude-mpm verify --service kuzu-memory

# Get JSON output for automation
claude-mpm verify --json

# Manage memory for large conversation histories
claude-mpm cleanup-memory
```

See [QUICKSTART.md](QUICKSTART.md) for complete usage examples.


## Architecture (v4.4.1)

Following Phase 3 architectural simplification in v4.4.1, Claude MPM features:

- **Streamlined Rich Interface**: Removed complex TUI system (~2,500 lines) for cleaner user experience
- **Optional MCP Services**: mcp-vector-search and kuzu-memory with automatic fallback installation
- **Persistent Knowledge System**: Project-specific kuzu-memory databases with intelligent prompt enrichment
- **Service-Oriented Architecture**: Simplified five specialized service domains
- **Interface-Based Contracts**: All services implement explicit interfaces
- **Enhanced Performance**: ~3,700 lines removed for better startup time and maintainability
- **Enhanced Security**: Comprehensive input validation and sanitization framework

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


## 📚 Documentation

**👉 [Complete Documentation Hub](docs/README.md)** - Start here for all documentation!

### Quick Links by User Type

#### 👥 For Users
- **[🚀 5-Minute Quick Start](docs/user/quickstart.md)** - Get running immediately
- **[📦 Installation Guide](docs/user/installation.md)** - All installation methods
- **[📖 User Guide](docs/user/README.md)** - Complete user documentation
- **[❓ FAQ](docs/user/faq.md)** - Common questions answered

#### 💻 For Developers
- **[🏗️ Architecture Overview](docs/developer/ARCHITECTURE.md)** - Service-oriented system design
- **[💻 Developer Guide](docs/developer/README.md)** - Complete development documentation
- **[🧪 Contributing](docs/developer/03-development/README.md)** - How to contribute
- **[📊 API Reference](docs/API.md)** - Complete API documentation

#### 🤖 For Agent Creators
- **[🤖 Agent System](docs/AGENTS.md)** - Complete agent development guide
- **[📝 Creation Guide](docs/developer/07-agent-system/creation-guide.md)** - Step-by-step tutorials
- **[📋 Schema Reference](docs/developer/10-schemas/agent_schema_documentation.md)** - Agent format specifications

#### 🚀 For Operations
- **[🚀 Deployment](docs/DEPLOYMENT.md)** - Release management & versioning
- **[📊 Monitoring](docs/MONITOR.md)** - Real-time dashboard & metrics
- **[🐛 Troubleshooting](docs/TROUBLESHOOTING.md)** - Enhanced `doctor` command with detailed reports and auto-fix capabilities

### 🎯 Documentation Features
- **Single Entry Point**: [docs/README.md](docs/README.md) is your navigation hub
- **Clear User Paths**: Organized by user type and experience level
- **Cross-Referenced**: Links between related topics and sections
- **Up-to-Date**: Version 4.3.3 with current information

## Recent Updates (v4.3.3)

**Enhanced PM Instructions**: PM2 deployment support and mandatory web-qa verification for quality assurance.

**Improved Version Management**: Better version comparison logic and agent override warnings for smoother operations.

**Code Quality Improvements**: Auto-fix code formatting and import management with enhanced standard tools recognition.

**Documentation Overhaul**: Unified documentation architecture with single entry point and clear navigation paths.

**Performance Enhancements**: Continued 50-80% performance improvements through intelligent caching and lazy loading.

See [CHANGELOG.md](CHANGELOG.md) for full history and [docs/user/MIGRATION.md](docs/user/MIGRATION.md) for upgrade instructions.

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
- Enhanced for [Claude Code (CLI)](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
