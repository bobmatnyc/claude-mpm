# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for **Claude Code (CLI)** that enables multi-agent workflows, session management, and real-time monitoring through a streamlined Rich-based interface.

> **⚠️ Important**: Claude MPM extends **Claude Code (CLI)**, not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.

> **Quick Start**: See [QUICKSTART.md](QUICKSTART.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: 15 specialized agents for comprehensive project management
- 🎯 **Skills System**: 20 bundled skills with auto-linking, three-tier organization (bundled/user/project), and interactive configuration
- 🧠 **Persistent Knowledge System**: Project-specific kuzu-memory integration for intelligent context retention
- 🔄 **Session Management**: Resume previous sessions with `--resume`
- 📋 **Resume Log System**: Proactive context management with automatic 10k-token session logs at 70%/85%/95% thresholds
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 🔌 **Smart MCP Services**: Interactive auto-install for mcp-vector-search on first use (pip/pipx choice)
- 🔍 **Semantic Code Search**: Optional vector search with graceful fallback to grep/glob
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
- `[mcp]` - Include MCP services (mcp-vector-search, mcp-browser, mcp-ticketer)
- `[monitor]` - Full monitoring dashboard with Socket.IO and async web server components
- **Combine both**: Use `"claude-mpm[mcp,monitor]"` to install all features
- **Note**: kuzu-memory is now a required dependency, always included with Claude MPM
- **Auto-Install**: mcp-vector-search offers interactive installation on first use (pip/pipx choice)
- Without pre-installed MCP dependencies, services install on-demand with user confirmation

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

# Use semantic code search (auto-installs mcp-vector-search on first use)
claude-mpm search "authentication logic"
# or inside Claude Code session:
/mpm-search "authentication logic"

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

### Skills System

Claude MPM includes a powerful skills system that eliminates redundant agent guidance through reusable skill modules:

**20 Bundled Skills** covering essential development workflows (all versioned starting at 0.1.0):
- Git workflow, TDD, code review, systematic debugging
- API documentation, refactoring patterns, performance profiling
- Docker containerization, database migrations, security scanning
- JSON/PDF/XLSX handling, async testing, ImageMagick operations
- Local development servers: Next.js, FastAPI, Vite, Express
- Web performance: Lighthouse metrics, Core Web Vitals optimization

**Three-Tier Organization:**
- **Bundled**: Core skills included with Claude MPM (~15,000 lines of reusable guidance)
- **User**: Custom skills in `~/.config/claude-mpm/skills/`
- **Project**: Project-specific skills in `.claude-mpm/skills/`

**Version Tracking:**
- All skills support semantic versioning (MAJOR.MINOR.PATCH)
- Check versions with `/mpm-version` command in Claude Code
- See [Skills Versioning Guide](docs/user/skills-versioning.md) for details

**Quick Access:**
```bash
# Interactive skills management
claude-mpm configure
# Choose option 2: Skills Management

# Auto-link skills to agents based on their roles
# Configure custom skill assignments
# View current skill mappings
```

Skills are automatically injected into agent prompts, reducing template size by 85% while maintaining full capability coverage.

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

### Resume Log System

**NEW in v4.17.2** - Proactive context management for seamless session continuity.

The Resume Log System automatically generates structured 10k-token logs when approaching Claude's context window limits, enabling you to resume work without losing important context.

**Key Features**:
- 🎯 **Graduated Thresholds**: Warnings at 70% (60k buffer), 85% (30k buffer), and 95% (10k buffer)
- 📋 **Structured Logs**: 10k-token budget intelligently distributed across 7 key sections
- 🔄 **Seamless Resumption**: Automatically loads previous session context on startup
- 📁 **Human-Readable**: Markdown format for both Claude and human review
- ⚙️ **Zero-Configuration**: Works automatically with sensible defaults

**How It Works**:
1. Monitor token usage continuously throughout session
2. Display proactive warnings at 70%, 85%, and 95% thresholds
3. Automatically generate resume log when approaching limits
4. Load previous resume log when starting new session
5. Continue work seamlessly with full context preservation

**Example Resume Log Structure**:
```markdown
# Session Resume Log: 20251101_115000

## Context Metrics (500 tokens)
- Token usage and percentage

## Mission Summary (1,000 tokens)
- Overall goal and purpose

## Accomplishments (2,000 tokens)
- What was completed

## Key Findings (2,500 tokens)
- Important discoveries

## Decisions & Rationale (1,500 tokens)
- Why choices were made

## Next Steps (1,500 tokens)
- What to do next

## Critical Context (1,000 tokens)
- Essential state, IDs, paths
```

**Configuration** (`.claude-mpm/configuration.yaml`):
```yaml
context_management:
  enabled: true
  budget_total: 200000
  thresholds:
    caution: 0.70   # First warning - plan transition
    warning: 0.85   # Strong warning - wrap up
    critical: 0.95  # Urgent - stop new work
  resume_logs:
    enabled: true
    auto_generate: true
    max_tokens: 10000
    storage_dir: ".claude-mpm/resume-logs"
```

**QA Status**: 40/41 tests passing (97.6% coverage), APPROVED FOR PRODUCTION ✅

See [docs/user/resume-logs.md](docs/user/resume-logs.md) for complete documentation.

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
- **Up-to-Date**: Version 4.16.3 with web performance optimization skill

## Recent Updates (v4.16.3)

**Web Performance Optimization**: New `web-performance-optimization` skill for Lighthouse metrics, Core Web Vitals (LCP, INP, CLS), and framework-specific optimization patterns.

## Previous Updates (v4.16.1)

**Local Development Skills**: Added 4 new toolchain-specific skills: `nextjs-local-dev`, `fastapi-local-dev`, `vite-local-dev`, and `express-local-dev` for professional local server management with PM2, HMR, and production-grade patterns.

**Skills System Integration**: 20 bundled skills with auto-linking, three-tier organization, and interactive configuration. Eliminates 85% of redundant guidance across agent templates (~15,000 lines of reusable content).

**Enhanced Documentation**: Complete documentation suite with PDF guides, reorganized structure, and comprehensive design documents for skills integration.

**Agent Template Improvements**: Cleaned agent templates with skills integration, removing redundant guidance while maintaining full capability coverage.

**Interactive Skills Management**: New skills wizard accessible via `claude-mpm configure` for viewing, configuring, and auto-linking skills to agents.

**Bug Fixes**: Resolved agent template inconsistencies and improved configuration management.

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
