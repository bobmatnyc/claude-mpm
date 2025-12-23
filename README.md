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

## 🚀 What's New in v5.0

### Git Repository Integration for Agents & Skills

Claude MPM now supports **Git repositories** for distributing and managing agents and skills - the most requested feature from our community!

**🎯 Key Highlights:**
- **📦 Massive Library**: 47+ agents and hundreds of skills deployed automatically from curated repositories
- **🏢 Official Content**: Anthropic's official skills repository included by default
- **🔧 Fully Extensible**: Add your own agent/skill repositories with immediate testing
- **🌳 Smart Organization**: Hierarchical BASE-AGENT.md inheritance for shared templates
- **📊 Clear Visibility**: Two-phase progress bars show sync and deployment status
- **✅ Fail-Fast Testing**: Test repositories before they cause startup issues

#### Quick Start: Add Your Own Repository

```bash
# Add custom agent repository (with immediate testing)
claude-mpm agent-source add https://github.com/yourorg/your-agents

# Add custom skill repository
claude-mpm skill-source add https://github.com/yourorg/your-skills

# Test repository without saving
claude-mpm agent-source add https://github.com/yourorg/your-agents --test

# List all configured sources
claude-mpm agent-source list
```

#### Default Repositories

**Agents** (47+ agents):
- 🏢 System: `bobmatnyc/claude-mpm-agents` - Core agent templates

**Skills** (hundreds of skills):
- 🏢 System: `bobmatnyc/claude-mpm-skills` - Community skills
- 🎯 Official: `anthropics/skills` - Anthropic's official skills (14+ skills)

**What This Means:**
- ✅ **Automatic Setup**: Everything deploys on first run
- ✅ **Always Updated**: Git repositories sync on startup
- ✅ **Nested Support**: Repositories with subdirectories are automatically flattened
- ✅ **Template Inheritance**: BASE-AGENT.md files cascade from parent directories
- ✅ **Priority System**: Control which sources win when multiple repos provide the same agent/skill

#### Hierarchical Organization Example

Support for BASE-AGENT.md enables powerful template inheritance:

```
your-agents/
  BASE-AGENT.md              # Root shared content (all agents inherit)
  engineering/
    BASE-AGENT.md            # Engineering-specific (engineering/* agents inherit)
    python/
      fastapi-engineer.md    # Inherits both BASE files
```

See [docs/features/hierarchical-base-agents.md](docs/features/hierarchical-base-agents.md) for complete guide.

## Features

### 🎯 Multi-Agent Orchestration

- **47+ Specialized Agents**: Comprehensive coverage from Git repositories (Python, Rust, QA, Security, Ops, etc.)
- **Smart Task Routing**: PM agent intelligently delegates work to specialist agents
- **Session Management**: Resume previous sessions with `--resume`
- **Resume Log System**: Proactive context management with automatic 10k-token session logs at 70%/85%/95% thresholds

### 📦 Git Repository Integration (NEW in v5.0)

- **🏢 Curated Content**: Default repositories with 47+ agents and hundreds of skills
- **🎯 Official Skills**: Anthropic's official skills included by default
- **🔧 Custom Repositories**: Add your own via CLI or configuration
- **🌳 Nested Support**: Automatic flattening of nested directory structures
- **📝 Template Inheritance**: BASE-AGENT.md for hierarchical organization
- **✅ Immediate Testing**: Fail-fast validation when adding repositories
- **📊 Progress Visibility**: Two-phase progress bars (sync + deployment)
- **⚡ Smart Caching**: ETag-based caching reduces bandwidth by 95%+

### 🎯 Skills System

- **Hundreds of Skills**: Comprehensive skill library from curated repositories
- **Official Skills**: 14+ skills from Anthropic's official repository
- **Three-Tier Organization**: Bundled/user/project skills with priority resolution
- **Auto-Linking**: Skills automatically linked to relevant agents
- **Interactive Configuration**: Skills wizard via `claude-mpm configure`
- **Version Tracking**: Semantic versioning for all skills

### 🔌 Advanced Integration

- **MCP Integration**: Full support for Model Context Protocol services
- **Real-Time Monitoring**: Live dashboard with `--monitor` flag
- **Multi-Project Support**: Per-session working directories
- **Git Integration**: View diffs and track changes across projects

### ⚡ Performance & Security

- **Simplified Architecture**: ~3,700 lines removed for better performance
- **Enhanced Security**: Comprehensive input validation and sanitization
- **Intelligent Caching**: File-based instruction caching for optimal performance
  - ✅ Eliminates ARG_MAX limits on Linux (exceeds by 19.1%) and Windows (exceeds by 476%)
  - ✅ ~200ms faster agent startup with hash-based cache invalidation
  - ✅ Automatic and transparent (no configuration required)

## Quick Installation

### Prerequisites

**Before installing Claude MPM**, ensure you have:

1. **Python 3.11+** (required for kuzu-memory dependency)
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

# Or with uv (faster)
uv tool install claude-mpm

# Install with monitoring dashboard (recommended)
pip install "claude-mpm[monitor]"
uv tool install "claude-mpm[monitor]"
```

Or with pipx/uvx (recommended for isolated installation):
```bash
# Basic installation
pipx install claude-mpm

# Or with uv tool (permanent installation)
uv tool install claude-mpm

# Or with uvx (one-off execution)
uvx claude-mpm

# Install with monitoring dashboard (recommended)
pipx install "claude-mpm[monitor]"
uv tool install "claude-mpm[monitor]"
```

### Verify Installation

```bash
# Check versions
claude-mpm --version
claude --version

# Run diagnostics (checks Claude Code compatibility)
claude-mpm doctor

# Verify Git repositories are synced
ls ~/.claude/agents/    # Should show 47+ agents
ls ~/.claude/skills/    # Should show hundreds of skills

# Check agent sources
claude-mpm agent-source list

# Check skill sources
claude-mpm skill-source list
```

**What You Should See:**
- ✅ 47+ agents deployed to `~/.claude/agents/`
- ✅ Hundreds of skills deployed to `~/.claude/skills/`
- ✅ Two agent sources configured (system + official)
- ✅ Two skill sources configured (system + official)
- ✅ Progress bars showing sync and deployment phases

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
# Or with uv
uv tool install kuzu-memory
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
# Or with uv
uv tool install mcp-vector-search
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

# Or with uv
uv tool install kuzu-memory
uv tool install mcp-vector-search
```

Then verify they're working:

```bash
claude-mpm verify
```

**That's it!** These tools integrate automatically with Claude MPM once installed. No additional configuration needed.

**That's it!** See [docs/user/getting-started.md](docs/user/getting-started.md) for immediate usage.

## Cache Management

Claude MPM maintains a local cache of agent templates at `~/.claude-mpm/cache/agents/`.

### Cache Structure

```
~/.claude-mpm/cache/agents/
└── bobmatnyc/
    └── claude-mpm-agents/
        ├── .git/              # Git repository
        ├── agents/            # 45+ agent templates
        └── docs/
```

> **Note**: Prior to v5.4.23, agents were cached to `~/.claude-mpm/cache/remote-agents/`. This has been standardized to `~/.claude-mpm/cache/agents/`. Existing caches are automatically migrated.

### Git Workflow (Optional)

If your cache is a git repository, you can manage agents with git operations:

```bash
# Check cache status
claude-mpm agents cache-status

# Pull latest agents
claude-mpm agents cache-pull

# Commit local changes
claude-mpm agents cache-commit --message "feat: update agents"

# Push changes
claude-mpm agents cache-push

# Full sync workflow
claude-mpm agents cache-sync
```

**Or use Makefile targets:**

```bash
make agents-cache-status   # Show git status
make agents-cache-pull     # Pull latest
make agents-cache-sync     # Full sync (pull + commit + push)
make deploy-agents         # Deploy with auto-pull
```

### HTTP Sync Fallback

If cache is not a git repository, Claude MPM automatically falls back to HTTP sync with GitHub API.

### Migration from Legacy Cache

If you have an old `cache/agents/` directory, run the migration script:

```bash
python scripts/migrate_cache_to_remote_agents.py
```

**See also:** [docs/CACHE_MANAGEMENT.md](docs/CACHE_MANAGEMENT.md) for comprehensive cache management guide.

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

## Managing Agent & Skill Repositories

Claude MPM uses **Git repositories** to distribute and manage agents and skills. This provides automatic updates, version control, and easy sharing of agent/skill libraries.

### Quick Start

```bash
# Add custom agent repository
claude-mpm agent-source add https://github.com/yourorg/your-agents

# Add custom skill repository
claude-mpm skill-source add https://github.com/yourorg/your-skills

# Test repository without saving (fail-fast validation)
claude-mpm agent-source add https://github.com/yourorg/your-agents --test

# List configured sources
claude-mpm agent-source list
claude-mpm skill-source list

# Update from all sources
claude-mpm agent-source update
claude-mpm skill-source update
```

### Priority System

When multiple sources provide the same agent/skill, priority controls which one wins:

- **Lower number = Higher precedence** (priority 10 beats priority 100)
- **Local agents/skills** (`.claude-mpm/agents/`, `.claude-mpm/skills/`) always override
- **System defaults** provide fallback

**Example Configuration:**

```yaml
# ~/.claude-mpm/config/agent_sources.yaml
repositories:
  - url: https://github.com/myteam/agents
    priority: 10    # Highest precedence (custom agents)

  - url: https://github.com/bobmatnyc/claude-mpm-agents
    priority: 100   # System default (official agents)
```

### Hierarchical Organization with BASE-AGENT.md

Support for BASE-AGENT.md enables powerful template inheritance:

```
your-agents/
  BASE-AGENT.md              # Root shared content (all agents inherit)
  engineering/
    BASE-AGENT.md            # Engineering-specific (engineering/* inherit)
    python/
      fastapi-engineer.md    # Inherits both BASE files
      django-engineer.md     # Inherits both BASE files
    rust/
      systems-engineer.md    # Inherits both BASE files
```

**How It Works:**
1. **Cascading Inheritance**: Each agent inherits from all BASE-AGENT.md files in parent directories
2. **Automatic Flattening**: Nested repositories are automatically flattened during deployment
3. **DRY Templates**: Share common instructions across related agents
4. **Maintainability**: Update shared content in one place

See [docs/features/hierarchical-base-agents.md](docs/features/hierarchical-base-agents.md) for complete guide.

### Configuration via YAML

Edit configuration files directly:
- **Agents**: `~/.claude-mpm/config/agent_sources.yaml`
- **Skills**: `~/.claude-mpm/config/skill_sources.yaml`

**Example agent_sources.yaml:**

```yaml
repositories:
  - url: https://github.com/bobmatnyc/claude-mpm-agents
    priority: 100
    enabled: true

  - url: https://github.com/yourorg/custom-agents
    priority: 10
    enabled: true
```

### Benefits

✅ **Always Up-to-Date**: Repositories sync automatically on startup
✅ **Bandwidth Efficient**: ETag-based caching reduces network usage by 95%+
✅ **Version Control**: Track changes through Git history
✅ **Immediate Testing**: Fail-fast validation prevents startup issues
✅ **Nested Support**: Automatic flattening of directory structures
✅ **Template Inheritance**: BASE-AGENT.md for DRY principles
✅ **Progress Visibility**: Two-phase progress bars (sync + deployment)
✅ **Community Access**: Latest improvements available immediately
✅ **Organization Libraries**: Share team-specific content across projects

### Documentation

- **[Agent Sources User Guide](docs/user/agent-sources.md)** - Complete guide with examples
- **[CLI Reference](docs/reference/cli-agent-source.md)** - All `agent-source` commands
- **[Hierarchical BASE-AGENT.md](docs/features/hierarchical-base-agents.md)** - Template inheritance guide
- **[Migration Guide](docs/migration/agent-sources-git-default-v4.5.0.md)** - Upgrading from v4.4.x
- **[Troubleshooting](docs/user/troubleshooting.md#agent-source-issues)** - Common issues and solutions

## Skills Deployment

Skills are automatically deployed from Git repositories, just like agents. Claude MPM includes **hundreds of skills** from curated repositories:

- **System Skills**: Community skills from `bobmatnyc/claude-mpm-skills`
- **Official Skills**: Anthropic's official skills from `anthropics/skills`
- **Custom Skills**: Add your own skill repositories

### Quick Usage

```bash
# Skills are automatically deployed on first run
# No manual deployment needed!

# Add custom skill repository
claude-mpm skill-source add https://github.com/yourorg/custom-skills

# List configured skill sources
claude-mpm skill-source list

# Update skills from all sources
claude-mpm skill-source update
```

### How Skills Work

1. **Automatic Deployment**: All skills from configured repositories deploy on startup
2. **Three-Tier Organization**:
   - **Bundled**: System and official skills (hundreds)
   - **User**: Custom skills in `~/.config/claude-mpm/skills/`
   - **Project**: Project-specific skills in `.claude-mpm/skills/`
3. **Priority Resolution**: Project → User → Bundled (local always wins)
4. **Auto-Linking**: Skills automatically linked to relevant agents
5. **Version Tracking**: All skills support semantic versioning

### Technology → Skills Mapping

The Research agent automatically analyzes your project and recommends relevant skills:

| Your Technology | Auto-Recommended Skills |
|-----------------|-------------------------|
| Python + pytest | test-driven-development, python-style |
| FastAPI/Flask | backend-engineer |
| React/Next.js | frontend-development, web-frameworks |
| Docker | docker-workflow |
| GitHub Actions | ci-cd-pipeline-builder |
| Playwright | webapp-testing |

### Interactive Management

```bash
# Interactive skills wizard
claude-mpm configure
# Choose option 2: Skills Management

# Features:
# - View all deployed skills
# - Configure skill assignments to agents
# - Auto-link skills based on agent roles
# - Manage custom skill repositories
```

### Important Notes

- ⚠️ Skills load at **Claude Code startup only** - restart required after adding repositories
- ✅ Batch add related skill repositories to minimize restarts
- ✅ Research agent automatically recommends missing skills during project analysis
- See [Skills Deployment Guide](docs/guides/skills-deployment-guide.md) for comprehensive details
- See [Skills Quick Reference](docs/reference/skills-quick-reference.md) for command reference


## Architecture

Claude MPM features a clean, service-oriented architecture:

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

**NEW in v5.4.13**: Runtime memory loading for instant updates and better efficiency.

**How It Works:**
- **Memory Files**: Store agent memories in `.claude-mpm/memories/{agent_id}.md` (e.g., `engineer.md`, `qa.md`)
- **Runtime Loading**: Memories loaded dynamically when agents are delegated to (no restart required)
- **Instant Updates**: Memory changes take effect immediately
- **Event Observability**: Memory loading tracked via EventBus (`agent.memory.loaded` events)

**Memory Format:**
Agents learn project-specific patterns using a simple markdown list format and can update memories via JSON response fields (`remember` for incremental updates, `MEMORIES` for complete replacement).

**See:** [Memory Flow Architecture](docs/architecture/memory-flow.md) for complete technical details.

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

See [docs/reference/MEMORY.md](docs/reference/MEMORY.md) and [docs/developer/11-dashboard/README.md](docs/developer/11-dashboard/README.md) for details.


## 📚 Documentation

**👉 [Complete Documentation Hub](docs/README.md)** - Start here for all documentation!

### Quick Links by User Type

#### 👥 For Users
- **[🚀 5-Minute Quick Start](docs/user/quickstart.md)** - Get running immediately
- **[📦 Installation Guide](docs/user/installation.md)** - All installation methods
- **[📖 User Guide](docs/user/README.md)** - Complete user documentation
- **[❓ FAQ](docs/guides/FAQ.md)** - Common questions answered

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

## Recent Updates (v5.0) 🎉

**Major Release**: Git Repository Integration for Agents & Skills

**🚀 What's New:**
- **Git Repository Support**: Agents and skills now deploy from Git repositories
- **47+ Agents**: Comprehensive agent library from curated repositories
- **Hundreds of Skills**: System skills + Official Anthropic skills automatically deployed
- **Hierarchical BASE-AGENT.md**: Template inheritance for DRY principles
- **Nested Repository Support**: Automatic flattening of directory structures
- **Immediate Testing**: Fail-fast validation when adding repositories
- **Two-Phase Progress**: Clear visibility during sync and deployment
- **ETag Caching**: 95%+ bandwidth reduction with intelligent caching

**🔧 Repository Management:**
- `claude-mpm agent-source add/list/update` - Manage agent repositories
- `claude-mpm skill-source add/list/update` - Manage skill repositories
- Priority-based resolution for multiple sources
- YAML configuration support

**📚 Documentation:**
- Complete guides for Git repository integration
- Hierarchical BASE-AGENT.md documentation
- Migration guides for existing installations
- Troubleshooting and best practices

**🎯 Benefits:**
- Always up-to-date content from repositories
- Community-driven agent and skill libraries
- Easy sharing of organizational content
- Version control for all templates

See [CHANGELOG.md](CHANGELOG.md) for full history and [docs/user/MIGRATION.md](docs/user/MIGRATION.md) for upgrade instructions.

## 📜 License

[![License](https://img.shields.io/badge/License-Elastic_2.0-blue.svg)](LICENSE)

Licensed under the [Elastic License 2.0](LICENSE) - free for internal use and commercial products.

**Main restriction:** Cannot offer as a hosted SaaS service without a commercial license.

📖 [Licensing FAQ](LICENSE-FAQ.md) | 💼 Commercial licensing: bob@matsuoka.com

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
Contributions are welcome! Please see our [project structure guide](docs/reference/STRUCTURE.md) and follow the established patterns.

**Development Workflow**:
1. Run `make dev-complete` to set up your environment
2. Code formatting happens automatically on commit
3. All code must pass quality checks before merging

### Project Structure
See [docs/reference/STRUCTURE.md](docs/reference/STRUCTURE.md) for codebase organization.

## Credits

- Based on [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm)
- Enhanced for [Claude Code (CLI)](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
