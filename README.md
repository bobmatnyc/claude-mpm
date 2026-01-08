# Claude MPM - Multi-Agent Project Manager

A powerful orchestration framework for **Claude Code (CLI)** that enables multi-agent workflows, session management, and real-time monitoring through a streamlined Rich-based interface.

> **⚠️ Important**: Claude MPM **requires Claude Code CLI** (v2.0.30+), not Claude Desktop (app). All MCP integrations work with Claude Code's CLI interface only.
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

Claude MPM transforms Claude Code into a **multi-agent orchestration platform** with:

- **47+ Specialized Agents** - From Git repositories (Python, Rust, QA, Security, Ops, etc.)
- **Intelligent Task Routing** - PM agent delegates work to specialist agents
- **Session Management** - Resume previous sessions with full context preservation
- **Semantic Code Search** - AI-powered discovery of existing code and patterns
- **Real-Time Monitoring** - Live dashboard showing agent activity and performance
- **Git Repository Integration** - Always up-to-date agents and skills from curated repositories

---

## Quick Installation

### Prerequisites

1. **Python 3.10+** (3.11+ recommended)
2. **Claude Code CLI v2.0.30+** (required!)

```bash
# Verify Claude Code is installed
claude --version

# If not installed, get it from:
# https://docs.anthropic.com/en/docs/claude-code
```

### Install Claude MPM

**Homebrew (macOS):**
```bash
brew install claude-mpm --with-monitor
```

**pipx/uv (recommended):**
```bash
# With pipx
pipx install "claude-mpm[monitor]"

# Or with uv
uv tool install "claude-mpm[monitor]"
```

**pip:**
```bash
pip install "claude-mpm[monitor]"
```

### Verify Installation

```bash
# Check versions
claude-mpm --version
claude --version

# Run diagnostics
claude-mpm doctor

# Verify agents deployed
ls ~/.claude/agents/    # Should show 47+ agents
```

**What You Should See:**
- ✅ 47+ agents deployed to `~/.claude/agents/`
- ✅ 17 bundled skills (in Python package)
- ✅ Agent sources configured
- ✅ Progress bars showing sync and deployment

**💡 Recommended Partners**: Install [kuzu-memory](https://github.com/bobmatnyc/kuzu-memory) (persistent context) and [mcp-vector-search](https://github.com/bobmatnyc/mcp-vector-search) (semantic search) for enhanced capabilities.

**💡 Tool Version Management**: Use [ASDF version manager](docs/guides/asdf-tool-versions.md) to avoid Python/uv version conflicts across projects.

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
- **17 Bundled Skills** covering Git, TDD, Docker, API docs, testing, and more
- **Three-Tier Organization**: Bundled/user/project with priority resolution
- **Auto-Linking** to relevant agents based on roles
- **Custom Skills** via `.claude/skills/` or skill repositories

[→ Learn more: Skills Guide](docs/user/skills-guide.md)

### 🔍 Semantic Code Search
- **AI-Powered Discovery** with mcp-vector-search integration
- **Find by Intent** not just keywords ("authentication logic" finds relevant code)
- **Pattern Recognition** for discovering similar implementations
- **Live Updates** tracking code changes automatically

[→ Learn more: Developer Use Cases](docs/usecases/developers.md#semantic-code-search)

### 🔌 Advanced Integration
- **MCP Integration** with full Model Context Protocol support
- **Real-Time Monitoring** via `--monitor` flag and web dashboard
- **Multi-Project Support** with per-session working directories
- **Git Integration** with diff viewing and change tracking

[→ Learn more: MCP Gateway](docs/developer/13-mcp-gateway/README.md)

### ⚡ Performance & Security
- **Simplified Architecture** with ~3,700 lines removed for better performance
- **Enhanced Security** with comprehensive input validation
- **Intelligent Caching** with ~200ms faster startup via hash-based invalidation
- **Memory Management** with cleanup commands for large conversation histories

[→ Learn more: Architecture](docs/developer/ARCHITECTURE.md)

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
