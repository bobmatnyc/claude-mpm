# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for **Claude Code (CLI)** that enables multi-agent workflows, session management, and real-time monitoring through a streamlined Rich-based interface.

> **⚠️ Important**: Claude MPM **requires Claude Code CLI** (v1.0.92+), not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.
>
> **Don't have Claude Code?** Install from: https://docs.anthropic.com/en/docs/claude-code
>
> **Version Requirements:**
> - Minimum: v1.0.92 (hooks support)
> - Recommended: v2.0.30+ (latest features)

> **Quick Start**: See [docs/user/getting-started.md](docs/user/getting-started.md) to get running in 5 minutes!

## Features

- 🤖 **Multi-Agent System**: 15 specialized agents for comprehensive project management
- 🎯 **Skills System**: 20 bundled skills with auto-linking, three-tier organization (bundled/user/project), and interactive configuration
- 🔄 **Session Management**: Resume previous sessions with `--resume`
- 📋 **Resume Log System**: Proactive context management with automatic 10k-token session logs at 70%/85%/95% thresholds
- 📊 **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- 🔌 **MCP Integration**: Full support for Model Context Protocol services
- 📁 **Multi-Project Support**: Per-session working directories
- 🔍 **Git Integration**: View diffs and track changes across projects
- 🎯 **Smart Task Orchestration**: PM agent intelligently routes work to specialists
- ⚡ **Simplified Architecture**: ~3,700 lines removed for better performance and maintainability
- 🔒 **Enhanced Security**: Comprehensive input validation and sanitization framework

## Quick Installation

### Prerequisites

**Before installing Claude MPM**, ensure you have:

1. **Python 3.8+** (3.11+ recommended)
2. **Claude Code CLI v1.0.92+** (required!)

```bash
# Verify Claude Code is installed
claude --version

# If not installed, get it from:
# https://docs.anthropic.com/en/docs/claude-code
```

### Install Claude MPM

```bash
# Basic installation
pip install claude-mpm

# Install with monitoring dashboard (recommended)
pip install "claude-mpm[monitor]"
```

Or with pipx (recommended for isolated installation):
```bash
# Basic installation
pipx install claude-mpm

# Install with monitoring dashboard (recommended)
pipx install "claude-mpm[monitor]"
```

### Verify Installation

```bash
# Check versions
claude-mpm --version
claude --version

# Run diagnostics (checks Claude Code compatibility)
claude-mpm doctor
```

**💡 Optional Dependencies**:
- `[monitor]` - Full monitoring dashboard with Socket.IO and async web server components
- `[mcp]` - Additional MCP services (mcp-browser, mcp-ticketer) - most users won't need this

**🎉 Pipx Support Now Fully Functional!** Recent improvements ensure complete compatibility:
- ✅ Socket.IO daemon script path resolution (fixed)
- ✅ Commands directory access (fixed)
- ✅ Resource files properly packaged for pipx environments
- ✅ Python 3.13+ fully supported

## 🤝 Recommended Partner Products

Claude MPM works excellently with these complementary MCP tools. While optional, we **strongly recommend** installing them for enhanced capabilities:

### kuzu-memory - Advanced Memory Management

**What it does**: Provides persistent, project-specific knowledge graphs that enable agents to learn and retain context across sessions. Your agents will remember project patterns, architectural decisions, and important context automatically.

**Installation:**
```bash
pipx install kuzu-memory
```

**Benefits with Claude MPM:**
- 🧠 **Persistent Context**: Agents remember project-specific patterns and decisions across sessions
- 🎯 **Intelligent Prompts**: Automatically enriches agent prompts with relevant historical context
- 📊 **Knowledge Graphs**: Structured storage of project knowledge, not just flat memory
- 🔄 **Seamless Integration**: Works transparently in the background with zero configuration
- 💡 **Smart Learning**: Agents improve over time as they learn your project's patterns

**Perfect for**: Long-running projects, teams needing consistent context, complex codebases with deep architectural patterns.

**Learn more**: [kuzu-memory on PyPI](https://pypi.org/project/kuzu-memory/) | [GitHub Repository](https://github.com/bobmatnyc/kuzu-memory)

---

### mcp-vector-search - Semantic Code Search

**What it does**: Enables semantic code search across your entire codebase using AI embeddings. Find code by what it *does*, not just what it's *named*. Search for "authentication logic" and find relevant functions even if they're named differently.

**Installation:**
```bash
pipx install mcp-vector-search
```

**Benefits with Claude MPM:**
- 🔍 **Semantic Discovery**: Find code by intent and functionality, not just keywords
- 🎯 **Context-Aware**: Understand code relationships and similarities automatically
- ⚡ **Fast Indexing**: Efficient vector embeddings for large codebases
- 🔄 **Live Updates**: Automatically tracks code changes and updates index
- 📊 **Pattern Recognition**: Discover similar code patterns and potential refactoring opportunities

**Use with**: `/mpm-search "authentication logic"` command in Claude Code sessions or `claude-mpm search` CLI command.

**Perfect for**: Large codebases, discovering existing functionality, finding similar implementations, architectural exploration.

**Learn more**: [mcp-vector-search on PyPI](https://pypi.org/project/mcp-vector-search/) | [GitHub Repository](https://github.com/bobmatnyc/mcp-vector-search)

---

### Quick Setup - Both Tools

Install both recommended tools in one go:

```bash
pipx install kuzu-memory
pipx install mcp-vector-search
```

Then verify they're working:

```bash
claude-mpm verify
```

**That's it!** These tools integrate automatically with Claude MPM once installed. No additional configuration needed.

**That's it!** See [docs/user/getting-started.md](docs/user/getting-started.md) for immediate usage.

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

# Check for updates (including Claude Code compatibility)
claude-mpm doctor --checks updates
```

**💡 Update Checking**: Claude MPM automatically checks for updates and verifies Claude Code compatibility on startup. Configure in `~/.claude-mpm/configuration.yaml` or see [docs/update-checking.md](docs/update-checking.md).

See [docs/user/getting-started.md](docs/user/getting-started.md) for complete usage examples.


## Architecture (v4.4.1)

Following Phase 3 architectural simplification in v4.4.1, Claude MPM features:

- **Streamlined Rich Interface**: Removed complex TUI system (~2,500 lines) for cleaner user experience
- **MCP Integration**: Full support for Model Context Protocol services with automatic detection
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

#### Language-Specific Engineers
- **Python Engineer (v2.3.0)** - Type-safe, async-first Python with SOA patterns for non-trivial applications
  - Service-oriented architecture with ABC interfaces for applications
  - Lightweight script patterns for automation and one-off tasks
  - Clear decision criteria for when to use DI/SOA vs simple functions
  - Dependency injection containers with auto-resolution
  - Use for: Web applications, microservices, data pipelines (DI/SOA) or scripts, CLI tools, notebooks (simple functions)

- **Rust Engineer (v1.1.0)** - Memory-safe, high-performance systems with trait-based service architecture
  - Dependency injection with traits (constructor injection, trait objects)
  - Service-oriented architecture patterns (repository, builder)
  - Decision criteria for when to use DI/SOA vs simple code
  - Async programming with tokio and zero-cost abstractions
  - Use for: Web services, microservices (DI/SOA) or CLI tools, scripts (simple code)

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
