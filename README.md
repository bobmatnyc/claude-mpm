# Claude MPM - Multi-Agent Project Manager

[![PyPI version](https://badge.fury.io/py/claude-mpm.svg)](https://badge.fury.io/py/claude-mpm)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic_2.0-blue.svg)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

**A comprehensive workflow and agent management framework for Claude Code** that transforms your AI coding assistant into a full-featured development platform with multi-agent orchestration, skills system, MCP integration, session management, and semantic code search.

> **⚠️ Important**: Claude MPM **requires Claude Code CLI** (v2.1.3+), not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.
>
> **Don't have Claude Code?** Install from: https://docs.anthropic.com/en/docs/claude-code
>
> **Quick Start**: See [Getting Started Guide](docs/getting-started/README.md) to get running in 5 minutes!

---

## Who Should Use Claude MPM?

- 👥 **[Non-Technical Users (Founders/PMs)](docs/usecases/non-technical-users.md)** - Research and understand codebases using Research Mode - no coding experience required
- 💻 **[Developers](docs/usecases/developers.md)** - Multi-agent development workflows with semantic code search and advanced features
- 🏢 **[Teams](docs/usecases/teams.md)** - Collaboration patterns, session management, and coordinated workflows

---

## What is Claude MPM?

Claude MPM transforms Claude Code into a **comprehensive AI development platform** with:

### 🤖 Multi-Agent System
- **47+ Specialized Agents** - Python, TypeScript, Rust, Go, Java, Ruby, PHP, QA, Security, DevOps, and more
- **Intelligent PM Orchestration** - Automatic task routing to specialist agents
- **Agent Sources** - Deploy agents from Git repositories with ETag-based caching

### 🎯 Skills Framework
- **44+ Bundled Skills** - TDD, debugging, Docker, API design, security scanning, Git workflows
- **Progressive Disclosure** - Skills load on-demand to optimize context usage
- **Three-Tier Organization** - Bundled → User → Project priority resolution

### 🔌 MCP Integration (Model Context Protocol)
- **Google Workspace MCP** - 34 tools for Gmail, Calendar, Drive, Docs, Tasks
- **Notion** - 7 tools + bulk operations for databases, pages, markdown import
- **Confluence** - 7 tools + bulk operations for pages, spaces, CQL search
- **Slack** - User proxy for channels, messages, DMs, search
- **Semantic Code Search** - AI-powered code discovery via mcp-vector-search
- **Ticket Management** - GitHub, Linear, Jira integration via mcp-ticketer
- **Graph Memory** - Persistent project knowledge via kuzu-memory

### 📊 Session & Workflow Management
- **Session Resume** - Continue work with full context preservation
- **Auto-Pause** - Automatic context summaries at 70%/85%/95% thresholds
- **Real-Time Dashboard** - Live monitoring of agent activity
- **Hooks System** - 15+ event hooks for custom workflows

### 🔐 Enterprise Features
- **OAuth 2.0 Integration** - Secure Google Workspace authentication
- **Encrypted Token Storage** - Fernet encryption with system keychain
- **100+ CLI Commands** - Comprehensive management interface
- **60+ Services** - Service-oriented architecture with event bus

---

## Quick Installation

### Prerequisites

1. **Python 3.11-3.13** (Python 3.13 recommended; 3.14 NOT yet supported)
2. **Claude Code CLI v2.1.3+** (required!)
3. **GitHub Token** (recommended for skill sources)

> **Python Version Warning**:
> - macOS default Python 3.9 is **too old** - use `--python 3.13` flag
> - Python 3.13 is **recommended** and fully tested
> - Python 3.14 is **NOT yet supported** - installation will fail

```bash
# Verify Claude Code is installed
claude --version

# If not installed, get it from:
# https://docs.anthropic.com/en/docs/claude-code

# Set GitHub token (recommended - avoids rate limits)
export GITHUB_TOKEN=your_github_token
```

### Install Claude MPM

**IMPORTANT**: Install from your **home directory**, NOT from within a cloned git repository.

**uv (recommended):**
```bash
# From home directory (IMPORTANT!)
cd ~

# Install with Python 3.13 (not 3.9 or 3.14)
uv tool install claude-mpm[monitor,data-processing] --python 3.13
```

**Homebrew (macOS):**
```bash
brew tap bobmatnyc/tools
brew install claude-mpm
```

**pipx:**
```bash
cd ~
pipx install "claude-mpm[monitor]"
```

### Post-Installation Setup (Required)

These steps must be completed **before** running `claude-mpm doctor`:

```bash
# Create required directories
mkdir -p ~/.claude/{responses,memory,logs}

# Deploy agents
claude-mpm agents deploy

# Add skill source (recommended)
claude-mpm skill-source add https://github.com/bobmatnyc/claude-mpm-skills
```

### Verify Installation

```bash
# Run diagnostics (after completing setup above)
claude-mpm doctor --verbose

# Check versions
claude-mpm --version
claude --version

# Auto-configure your project
cd ~/your-project
claude-mpm auto-configure
```

**What You Should See:**
- 47+ agents deployed to `~/.claude/agents/`
- 44+ bundled skills (in Python package)
- Agent sources configured
- All doctor checks passing

**Recommended Partners**: Install these companion tools for enhanced capabilities:
```bash
uv tool install kuzu-memory --python 3.13
uv tool install mcp-vector-search --python 3.13
uv tool install mcp-ticketer --python 3.13
uv tool install mcp-browser --python 3.13
```

**Tool Version Management**: Use [ASDF version manager](docs/guides/asdf-tool-versions.md) to avoid Python/uv version conflicts across projects.

---

## Key Features

### 🎯 Multi-Agent Orchestration
- **47+ Specialized Agents** from Git repositories covering all development needs
- **Smart Task Routing** via PM agent intelligently delegating to specialists
- **Session Management** with `--resume` flag for seamless continuity
- **Resume Log System** with automatic 10k-token summaries at 70%/85%/95% thresholds

[→ Learn more: Multi-Agent Development](docs/usecases/developers.md#multi-agent-development)

### 📦 Git Repository Integration
- **Curated Content** with 47+ agents automatically deployed from repositories
- **Always Up-to-Date** with ETag-based caching (95%+ bandwidth reduction)
- **Hierarchical BASE-AGENT.md** for template inheritance and DRY principles
- **Custom Repositories** via `claude-mpm agent-source add`

[→ Learn more: Agent Sources](docs/user/agent-sources.md)

### 🎯 Skills System
- **44+ Bundled Skills** covering Git, TDD, Docker, API design, security, debugging, and more
- **Three-Tier Organization**: Bundled/user/project with priority resolution
- **Auto-Linking** to relevant agents based on roles
- **Progressive Disclosure** - Skills load on-demand to optimize context
- **Custom Skills** via `.claude/skills/` or skill repositories

[→ Learn more: Skills Guide](docs/user/skills-guide.md)

### 🔍 Semantic Code Search
- **AI-Powered Discovery** with mcp-vector-search integration
- **Find by Intent** not just keywords ("authentication logic" finds relevant code)
- **Pattern Recognition** for discovering similar implementations
- **Live Updates** tracking code changes automatically

[→ Learn more: Developer Use Cases](docs/usecases/developers.md#semantic-code-search)

### 🧪 MPM Commander (ALPHA)
- **Multi-Project Orchestration** with autonomous AI coordination across codebases
- **Tmux Integration** for isolated project environments and session management
- **Event-Driven Architecture** with inbox system for cross-project communication
- **LLM-Powered Decisions** via OpenRouter for autonomous work queue processing
- **Real-Time Monitoring** with state tracking (IDLE, WORKING, BLOCKED, PAUSED, ERROR)
- ⚠️ **Experimental** - API and CLI interface subject to change

[→ Commander Documentation](docs/commander/usage-guide.md)

### 🔌 Advanced Integration
- **MCP Integration** with full Model Context Protocol support
- **MCP Session Server** (`mpm-session-server`) for programmatic session management
- **Real-Time Monitoring** via `--monitor` flag and web dashboard
- **Multi-Project Support** with per-session working directories
- **Git Integration** with diff viewing and change tracking

[→ Learn more: MCP Gateway](docs/developer/13-mcp-gateway/README.md) | [→ MCP Session Server](docs/mcp-session-server.md)

### 🔐 External Integrations
- **Browser-Based OAuth** for secure authentication with MCP services
- **Google Workspace MCP** built-in server with **34 tools** for:
  - **Gmail** (5 tools): Search, read, send, draft, reply
  - **Calendar** (6 tools): List, get, create, update, delete events
  - **Drive** (7 tools): Search, read, create folders, upload, delete, move files
  - **Docs** (4 tools): Create, read, append, markdown-to-doc conversion
  - **Tasks** (12 tools): Full task and task list management
- **Notion MCP** built-in server with **7 tools** + bulk operations:
  - Query databases, get/create/update pages, search, markdown import
  - Setup: `claude-mpm setup notion`
- **Confluence MCP** built-in server with **7 tools** + bulk operations:
  - Get/create/update pages, search with CQL, list spaces, markdown import
  - Setup: `claude-mpm setup confluence`
- **Slack MCP** user proxy with **12 tools**:
  - Channels, messages, DMs, search - acts as authenticated user
  - Setup: `claude-mpm setup slack`
- **Encrypted Token Storage** using Fernet encryption with system keychain
- **Automatic Token Refresh** handles expiration seamlessly

```bash
# Set up Google Workspace OAuth
claude-mpm oauth setup workspace-mcp

# Set up Notion (API token)
claude-mpm setup notion

# Set up Confluence (URL + API token)
claude-mpm setup confluence

# Set up Slack (OAuth user token)
claude-mpm setup slack

# Check token status
claude-mpm oauth status workspace-mcp

# List OAuth-capable services
claude-mpm oauth list
```

[→ Google Workspace Setup](docs/guides/oauth-setup.md) | [→ Notion Setup](docs/integrations/NOTION_SETUP.md) | [→ Confluence Setup](docs/integrations/CONFLUENCE_SETUP.md) | [→ Slack Setup](docs/integrations/SLACK_USER_PROXY_SETUP.md)

### ⚡ Performance & Security
- **Simplified Architecture** with ~3,700 lines removed for better performance
- **Enhanced Security** with comprehensive input validation
- **Intelligent Caching** with ~200ms faster startup via hash-based invalidation
- **Memory Management** with cleanup commands for large conversation histories

[→ Learn more: Architecture](docs/developer/ARCHITECTURE.md)

### ⚙️ Automatic Migrations
- **Seamless Updates** with automatic configuration migration on first startup after update
- **One-Time Fixes** for cache restructuring and configuration changes
- **Non-Blocking** failures log warnings but do not stop startup
- **Tracked** in `~/.claude-mpm/migrations.yaml`

[→ Learn more: Startup Migrations](docs/features/startup-migrations.md)

---

## Quick Usage

```bash
# Start interactive mode
claude-mpm

# Start with monitoring dashboard
claude-mpm run --monitor

# Resume previous session
claude-mpm run --resume

# Semantic code search
claude-mpm search "authentication logic"
# or inside Claude Code:
/mpm-search "authentication logic"

# Health diagnostics
claude-mpm doctor

# Verify MCP services
claude-mpm verify

# Manage memory
claude-mpm cleanup-memory
```

**💡 Update Checking**: Claude MPM automatically checks for updates and verifies Claude Code compatibility on startup. Configure in `~/.claude-mpm/configuration.yaml` or see [docs/update-checking.md](docs/update-checking.md).

[→ Complete usage examples: User Guide](docs/user/user-guide.md)

---

## What's New in v5.0

### Git Repository Integration for Agents & Skills

- **📦 Massive Library**: 47+ agents and hundreds of skills deployed automatically
- **🏢 Official Content**: Anthropic's official skills repository included by default
- **🔧 Fully Extensible**: Add your own repositories with immediate testing
- **🌳 Smart Organization**: Hierarchical BASE-AGENT.md inheritance
- **📊 Clear Visibility**: Two-phase progress bars (sync + deployment)
- **✅ Fail-Fast Testing**: Test repositories before they cause startup issues

**Quick Start with Custom Repositories:**
```bash
# Add custom agent repository
claude-mpm agent-source add https://github.com/yourorg/your-agents

# Add custom skill repository
claude-mpm skill-source add https://github.com/yourorg/your-skills

# Test repository without saving
claude-mpm agent-source add https://github.com/yourorg/your-agents --test
```

[→ Full details: What's New](CHANGELOG.md)

---

## Documentation

**📚 [Complete Documentation Hub](docs/README.md)** - Start here for all documentation!

### Quick Links by User Type

#### 👥 For Users
- **[🚀 5-Minute Quick Start](docs/user/quickstart.md)** - Get running immediately
- **[📦 Installation Guide](docs/user/installation.md)** - All installation methods
- **[📖 User Guide](docs/user/user-guide.md)** - Complete user documentation
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
- **[🐛 Troubleshooting](docs/TROUBLESHOOTING.md)** - Enhanced `doctor` command with auto-fix

---

## Integrations

Claude MPM supports multiple integrations for enhanced functionality. See **[Complete Integration Documentation](docs/integrations/README.md)** for detailed setup guides.

### Core Integrations

- **[kuzu-memory](docs/integrations/kuzu-memory.md)** - Graph-based semantic memory for project context
- **[mcp-vector-search](docs/integrations/mcp-vector-search.md)** - AI-powered semantic code search and discovery

### External Services

- **[Google Workspace MCP](docs/integrations/gworkspace-mcp.md)** - Gmail, Calendar, Drive, Docs, Tasks (67 tools)
- **[Slack](docs/integrations/slack.md)** - Slack workspace integration via user proxy
- **[Notion](docs/integrations/NOTION_SETUP.md)** - Notion databases and pages (7 MCP tools + bulk CLI)
- **[Confluence](docs/integrations/CONFLUENCE_SETUP.md)** - Confluence pages and spaces (7 MCP tools + bulk CLI)

### Quick Setup

```bash
# Setup any integration with one command
claude-mpm setup <integration>

# Examples:
claude-mpm setup kuzu-memory
claude-mpm setup mcp-vector-search
claude-mpm setup google-workspace-mcp
claude-mpm setup slack
claude-mpm setup notion
claude-mpm setup confluence

# Setup multiple at once
claude-mpm setup kuzu-memory mcp-vector-search google-workspace-mcp
```

**Integration Features:**
- One-command setup for all services
- Secure OAuth 2.0 authentication (Google Workspace, Slack)
- Encrypted token storage in system keychain
- Automatic token refresh
- MCP protocol for standardized tool interfaces
- Bulk CLI operations for high-performance batch processing

---

## Contributing

Contributions are welcome! Please see:
- **[Contributing Guide](docs/developer/03-development/README.md)** - How to contribute
- **[Code Formatting](docs/developer/CODE_FORMATTING.md)** - Code quality standards
- **[Project Structure](docs/reference/STRUCTURE.md)** - Codebase organization

**Development Workflow:**
```bash
# Complete development setup
make dev-complete

# Or step by step:
make setup-dev          # Install in development mode
make setup-pre-commit   # Set up automated code formatting
```

---

## 📜 License

[![License](https://img.shields.io/badge/License-Elastic_2.0-blue.svg)](LICENSE)

Licensed under the [Elastic License 2.0](LICENSE) - free for internal use and commercial products.

**Main restriction:** Cannot offer as a hosted SaaS service without a commercial license.

📖 [Licensing FAQ](LICENSE-FAQ.md) | 💼 Commercial licensing: bob@matsuoka.com

---

## Credits

- Based on [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm)
- Enhanced for [Claude Code (CLI)](https://docs.anthropic.com/en/docs/claude-code) integration
- Built with ❤️ by the Claude MPM community
