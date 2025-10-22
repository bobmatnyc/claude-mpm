# 📚 Claude MPM Documentation Hub

**Version 4.9.0** | Claude Multi-Agent Project Manager
**Last Updated**: October 17, 2025

Welcome to the complete documentation for Claude MPM (Multi-Agent Project Manager) - a powerful orchestration framework that extends Claude Code with multi-agent workflows, session management, and real-time monitoring.

## 🎯 Quick Navigation

### 👥 For Users
- [🚀 **Quick Start**](user/quickstart.md) - Get running in 5 minutes
- [📦 **Installation**](user/INSTALL.md) - All installation methods
- [📖 **User Guide**](user/README.md) - Complete user documentation
- [🧠 **Memory System**](user/03-features/memory-system.md) - Agent learning & persistence
- [❓ **FAQ**](user/faq.md) - Common questions answered

### 💻 For Developers
- [🏗️ **Architecture**](developer/ARCHITECTURE.md) - Service-oriented system design
- [💻 **Development**](developer/README.md) - Complete developer guide
- [🔧 **API Reference**](API.md) - Service interfaces & APIs
- [🧪 **Contributing**](developer/03-development/README.md) - How to contribute
- [🔍 **Testing**](developer/TESTING.md) - Quality assurance practices

### 🤖 For Agent Creators
- [🤖 **Agent System**](AGENTS.md) - Complete agent development guide
- [📝 **Creation Guide**](developer/07-agent-system/creation-guide.md) - Step-by-step tutorials
- [📋 **Schema Reference**](developer/10-schemas/agent_schema_documentation.md) - Agent format specifications
- [🔄 **Management**](developer/07-agent-system/README.md) - Agent lifecycle & deployment

### 🔧 Operations & DevOps
- [🚀 **Deployment**](DEPLOYMENT.md) - Release management & versioning
- [📊 **Monitoring**](MONITOR.md) - Real-time dashboard & metrics
- [🔌 **MCP Gateway**](developer/13-mcp-gateway/README.md) - Model Context Protocol integration
- [🐛 **Troubleshooting**](TROUBLESHOOTING.md) - Diagnostic & problem resolution

## ⚡ Quick Start - 3 Commands

```bash
# 1. Install (choose one)
pip install claude-mpm                    # Basic installation
pipx install "claude-mpm[monitor]"       # With monitoring dashboard

# 2. Auto-configure your project (NEW!)
claude-mpm auto-configure                 # Detect stack & configure agents

# 3. Run
claude-mpm run                            # Interactive mode
claude-mpm run --monitor                  # With real-time dashboard
```

**✨ That's it!** Auto-configuration detects your project's languages and frameworks, then deploys the right agents automatically. See [Quick Start Guide](user/quickstart.md) for detailed setup or continue below for comprehensive navigation.

## 📖 Documentation Sections

### 🎯 By User Type

| User Type | Start Here | Key Documents |
|-----------|------------|---------------|
| **New Users** | [Quick Start](user/quickstart.md) | [Installation](user/INSTALL.md), [Basic Usage](user/02-guides/basic-usage.md) |
| **Developers** | [Architecture](developer/ARCHITECTURE.md) | [Development Setup](developer/03-development/setup.md), [API Reference](API.md) |
| **Agent Creators** | [Agent System](AGENTS.md) | [Creation Guide](developer/07-agent-system/creation-guide.md), [Schema](developer/10-schemas/agent_schema_documentation.md) |
| **DevOps/Ops** | [Deployment](DEPLOYMENT.md) | [Monitoring](MONITOR.md), [Troubleshooting](TROUBLESHOOTING.md) |

### 🗂️ By Topic

#### 🚀 Getting Started
- [Installation Guide](user/INSTALL.md) - All installation methods (pip, pipx, development)
- [Quick Start](user/quickstart.md) - 5-minute setup and first run
- [Auto-Configuration](user/03-features/auto-configuration.md) - **NEW!** Automatic agent setup
- [Basic Usage](user/02-guides/basic-usage.md) - Essential commands and workflows
- [Migration Guide](user/MIGRATION.md) - Upgrading from previous versions

#### 🏗️ Core System
- [Architecture Overview](developer/ARCHITECTURE.md) - Service-oriented design & 5 domains
- [Service Layer Guide](developer/SERVICES.md) - Service development patterns
- [Performance Guide](developer/PERFORMANCE.md) - Optimization & caching (91% latency reduction in v4.8.2+)
- [Security Framework](reference/SECURITY.md) - Input validation & security measures

#### 🤖 Agent System
- [Agent Development](AGENTS.md) - Complete agent creation guide
- [Coding Agents Catalog](reference/CODING_AGENTS.md) - 7 specialized coding agents with benchmark scores
- [Benchmark Infrastructure](benchmarks/README.md) - Complete benchmark system & test suites (NEW)
- [Benchmark Quick Reference](reference/BENCHMARK_QUICKREF.md) - Performance scores & methodology
- [Agent Capabilities Reference](reference/AGENT_CAPABILITIES.md) - Complete capabilities & routing
- [Agent Testing Guide](developer/AGENT_TESTING.md) - 84-test lightweight benchmark methodology
- [Agent Deployment Log](reference/AGENT_DEPLOYMENT_LOG.md) - Deployment history & rollback
- [Three-Tier System](developer/07-agent-system/README.md) - PROJECT > USER > SYSTEM hierarchy
- [Agent Formats](developer/07-agent-system/formats.md) - Markdown, JSON, YAML support
- [Memory System](user/03-features/memory-system.md) - Agent learning & persistence

#### 🔧 Development
- [Development Workflow](developer/README.md) - Quality-first development process
- [Project Structure](developer/STRUCTURE.md) - File organization reference
- [Project Organization](reference/PROJECT_ORGANIZATION.md) - Organization standards & rules
- [Testing Strategy](developer/TESTING.md) - Unit, integration, E2E testing
- [Code Quality](developer/LINTING.md) - Automated formatting & quality checks
- [Contributing](developer/03-development/README.md) - How to contribute to the project

#### 🚀 Local Operations
- [Local Process Management](user/03-features/local-process-management.md) - **NEW!** Deploy & monitor local development servers
- [Process Management Architecture](developer/LOCAL_PROCESS_MANAGEMENT.md) - Developer guide & extension points
- [Local Ops CLI Commands](reference/LOCAL_OPS_COMMANDS.md) - Complete command reference
- [Local Agents](user/03-features/local-agents.md) - Project-specific agent customization

#### 📊 Operations
- [Real-Time Monitoring](MONITOR.md) - Web dashboard & live metrics
- [Deployment Process](DEPLOYMENT.md) - Version management & release workflow
- [Troubleshooting](TROUBLESHOOTING.md) - Common issues & diagnostic tools
- [MCP Gateway](developer/13-mcp-gateway/README.md) - External tool integration

## 💡 AI Agent Quick Reference

**For Claude Code/AI agents working with this project:**

| Task | Command | Documentation |
|------|---------|---------------|
| **Auto-configure** | `claude-mpm auto-configure` | [Auto-Configuration](user/03-features/auto-configuration.md) |
| **Run system** | `claude-mpm run` | [Quick Start](user/quickstart.md) |
| **Check quality** | `make quality` | [Development](developer/README.md) |
| **Fix code style** | `make lint-fix` | [Code Quality](developer/LINTING.md) |
| **Run tests** | `make test` | [Testing](developer/TESTING.md) |
| **Deploy locally** | `claude-mpm local-deploy start --command "npm run dev" --auto-restart` | [Local Process Management](user/03-features/local-process-management.md) |
| **Monitor deployment** | `claude-mpm local-deploy monitor <deployment-id>` | [Local Ops Commands](reference/LOCAL_OPS_COMMANDS.md) |
| **List agents** | `claude-mpm agents list --by-tier` | [Agent System](AGENTS.md) |
| **Create agent** | `claude-mpm agents create <name>` | [Creation Guide](developer/07-agent-system/creation-guide.md) |
| **Deploy agents** | `claude-mpm agents deploy` | [Agent Management](developer/07-agent-system/README.md) |
| **Monitor activity** | `claude-mpm run --monitor` | [Monitoring](MONITOR.md) |

## 🔄 Documentation Structure

```
docs/
├── README.md              # 📍 THIS FILE - Master documentation hub
├── user/                  # 👥 End-user documentation
│   ├── README.md         # User documentation index
│   ├── quickstart.md     # 5-minute setup guide
│   ├── installation.md   # Complete installation guide
│   ├── 01-getting-started/   # Setup and first steps
│   ├── 02-guides/            # How-to guides and tutorials
│   ├── 03-features/          # Feature-specific documentation
│   └── 04-reference/         # User reference materials
├── developer/             # 💻 Developer documentation
│   ├── README.md         # Developer documentation index
│   ├── ARCHITECTURE.md   # System architecture overview
│   ├── SERVICES.md       # Service layer development
│   ├── TESTING.md        # Testing strategies & practices
│   ├── 01-architecture/      # Architecture deep dives
│   ├── 02-core-components/   # Core system components
│   ├── 03-development/       # Development workflows
│   ├── 07-agent-system/      # Agent development system
│   ├── 11-dashboard/         # Dashboard & monitoring
│   └── 13-mcp-gateway/       # MCP protocol integration
├── reference/             # 📋 Technical references
│   ├── DEPLOY.md         # Deployment procedures
│   ├── SECURITY.md       # Security framework
│   └── VERSIONING.md     # Version management
├── agents/                # 🤖 Agent-specific documentation
├── api/                   # 📚 Auto-generated API docs
├── _archive/              # 🗃️ Historical documentation
└── _internal/             # 🔧 Internal maintenance docs
```

## 🆘 Getting Help

**Can't find what you need?**

1. **🎯 Use Quick Navigation** - Jump directly to your user type section above
2. **🔍 Search by Topic** - Browse the "By Topic" section for specific subjects
3. **📁 Check Documentation Structure** - Navigate the organized folder structure
4. **🗃️ Search Archives** - Historical docs in [`_archive/`](_archive/) (reorganized 2025-08)
5. **🐛 Browse Issues** - Known problems & solutions on GitHub
6. **📚 API Docs** - Auto-generated documentation in [`api/`](api/)

## 🎯 Common Workflows

### 🆕 First Time User
1. [Install Claude MPM](user/INSTALL.md) → Choose installation method
2. [Quick Start](user/quickstart.md) → Get running in 5 minutes
3. [Basic Usage](user/02-guides/basic-usage.md) → Learn essential commands
4. [Agent System](AGENTS.md) → Understand the agent framework

### 👨‍💻 Developer Setup
1. [Architecture Overview](developer/ARCHITECTURE.md) → Understand the system
2. [Development Setup](developer/03-development/setup.md) → Configure dev environment
3. [Quality Workflow](developer/README.md#quality-workflow) → Learn development process
4. [Testing Practices](developer/TESTING.md) → Understand testing strategy

### 🤖 Agent Creator
1. [Agent System Guide](AGENTS.md) → Learn agent concepts
2. [Creation Tutorial](developer/07-agent-system/creation-guide.md) → Build your first agent
3. [Schema Reference](developer/10-schemas/agent_schema_documentation.md) → Understand agent formats
4. [Management Commands](developer/07-agent-system/README.md) → Deploy and manage agents

### 🚀 Operations & Deployment
1. [Deployment Guide](DEPLOYMENT.md) → Learn release process
2. [Monitoring Setup](MONITOR.md) → Configure real-time monitoring
3. [Troubleshooting](TROUBLESHOOTING.md) → Diagnostic procedures
4. [Version Management](reference/VERSIONING.md) → Understand versioning strategy

## ✨ Key Features & Capabilities

- **🎯 Auto-Configuration (NEW v4.10.0)**: Automatically detect project stack and configure agents
  - Detects Python, Node.js, Rust, Go, and more
  - Identifies frameworks (FastAPI, Next.js, React, etc.)
  - Recommends agents with confidence scores (default 80%+)
  - Preview mode for safe exploration
  - 207 comprehensive tests with 76% coverage
- **🤖 Multi-Agent System**: 15+ specialized agents for comprehensive project management
- **💻 Coding Agents (v4.9.0)**: 7 specialized coding agents with benchmark scores
  - Python Engineer v2.0.0 (Python 3.13+, JIT) - 62.3% (C)
  - TypeScript Engineer v2.0.0 (TS 5.6+, branded types) - 66.8% (C+)
  - Next.js Engineer v2.0.0 (Next.js 15, App Router) - 65.8% (C+)
  - **NEW**: Go Engineer v1.0.0 (Go 1.24+, concurrency) - 62.6% (C)
  - **NEW**: Rust Engineer v1.0.0 (Rust 2024, WebAssembly) - 67.3% (C+)
  - PHP Engineer v2.0.0 (PHP 8.4-8.5, Laravel 12) - 60.8% (C)
  - Ruby Engineer v2.0.0 (Ruby 3.4 YJIT, Rails 8) - 68.1% (C+) 🥇 **Top Performer**
- **🧠 Agent Memory**: Persistent learning with simple JSON response field updates
- **🔄 Session Management**: Pause and resume sessions with complete context continuity (NEW in v4.8.5+)
  - Save session state with `claude-mpm mpm-init pause`
  - Restore with automatic change detection using `claude-mpm mpm-init resume`
  - Full context preservation: conversation, git state, todos, accomplishments
- **🚀 Local Process Management (NEW v4.13.0)**: Professional-grade local deployment with health monitoring
  - Three-tier health checks (HTTP, process, resource)
  - Auto-restart on crash with exponential backoff & circuit breaker
  - Memory leak detection & resource exhaustion prevention
  - Log error monitoring with pattern matching
  - 10 CLI commands for comprehensive process management
  - Configuration-driven via YAML (`.claude-mpm/local-ops-config.yaml`)
- **📊 Real-Time Monitoring**: Live dashboard with `--monitor` flag
- **🔌 MCP Gateway**: Model Context Protocol integration for extensible tools
- **📁 Multi-Project Support**: Per-session working directories with git integration
- **⚡ Performance Improvements (v4.8.2+)**:
  - **91% latency reduction** in hook system (108ms → 10ms)
  - Git branch caching with 5-minute TTL
  - Non-blocking HTTP fallback with thread pool
  - 50-80% overall improvement through intelligent caching and lazy loading
- **🔒 Security**: Comprehensive input validation and sanitization framework
- **🏗️ Service-Oriented**: Five specialized service domains with interface contracts
- **🧪 Comprehensive Testing**: 84-test lightweight benchmark with multi-dimensional scoring
  - Average agent score: 64.8% across all coding agents
  - Multi-dimensional evaluation (Correctness 40%, Idiomaticity 25%, Performance 20%, Best Practices 15%)
  - See [Benchmark Quick Reference](reference/BENCHMARK_QUICKREF.md)

## 🤝 Contributing

We welcome contributions! Please start with:
- [Contributing Guide](developer/03-development/README.md) - How to contribute
- [Development Standards](developer/README.md#documentation-standards) - Code quality requirements
- [Project Structure](developer/STRUCTURE.md) - Codebase organization
- [Architecture Guide](developer/ARCHITECTURE.md) - System design principles

## 📝 Documentation Standards

This documentation follows these principles:
- **Single Entry Point**: This file (docs/README.md) is the master hub
- **Clear User Paths**: Distinct navigation for users, developers, and operations
- **Scannable Format**: Headers, tables, and quick reference sections
- **Cross-Referenced**: Links between related sections and topics
- **Up-to-Date**: Version 4.7.3 with current build information

---

**💡 Quick Tip**: Bookmark this page! It's designed as your central navigation hub for all Claude MPM documentation. Use the Quick Navigation section above to jump directly to what you need.