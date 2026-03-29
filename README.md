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

> **Current stable version: v6.1.0** — plugin install path, binary consolidation, and auto-migration. See [Beta Guide](docs/beta-6.0.md) for v6.0 release notes.

---

## Quick Start

### Plugin Install (recommended for most users)

The fastest way to get started. No pip install required — provides hooks, 56 skills, slash commands, and MCP server config directly inside Claude Code.

```bash
# Add the MPM marketplace
claude plugin marketplace add bobmatnyc/claude-mpm-marketplace

# Install the plugin
claude plugin install claude-mpm@claude-mpm-marketplace
```

This gives you: **6 hook events**, **56 skills**, **2 slash commands** (`/mpm-status`, `/mpm-help`), and **MCP server configuration** — all without pip install.

### Full Install (for power users)

For CLI commands, multi-agent orchestration, monitoring dashboard, and all integrations:

```bash
# Install the full package (from home directory)
cd ~
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13

# Then also install the plugin for Claude Code integration
claude plugin marketplace add bobmatnyc/claude-mpm-marketplace
claude plugin install claude-mpm@claude-mpm-marketplace
```

See [Installation](#quick-installation) below for all installation methods.

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
- **56+ Bundled Skills** - TDD, debugging, Docker, API design, security scanning, Git workflows
- **Progressive Disclosure** - Skills load on-demand to optimize context usage
- **Three-Tier Organization** - Bundled → User → Project priority resolution
- **Domain Authority System** - Auto-generated agent/tool discovery skills for intelligent PM delegation
- **Skills Optimization** - Intelligent project analysis with automated skill recommendations

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

#### Option A: Plugin Only (no pip required)

```bash
# Add the MPM marketplace and install the plugin
claude plugin marketplace add bobmatnyc/claude-mpm-marketplace
claude plugin install claude-mpm@claude-mpm-marketplace
```

This provides hooks, 56 skills, slash commands, and MCP config. For the full CLI, agents, monitor, and dashboard, continue with Option B.

#### Option B: Full Install (pip + plugin)

**IMPORTANT**: Install from your **home directory**, NOT from within a cloned git repository.

**uv (recommended):**
```bash
# From home directory (IMPORTANT!)
cd ~

# Install with Python 3.13 (not 3.9 or 3.14)
uv tool install "claude-mpm[monitor,data-processing]" --python 3.13
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
- 56+ bundled skills (in Python package)
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
- **56+ Bundled Skills** covering Git, TDD, Docker, API design, security, debugging, and more
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
- **MCP Session Server** (`claude-mpm mcp serve session`) for programmatic session management
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
  - Setup: `claude-mpm setup slack-mpm`
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
claude-mpm setup slack-mpm

# Check token status
claude-mpm oauth status workspace-mcp

# List OAuth-capable services
claude-mpm oauth list
```

[→ Google Workspace Setup](docs/guides/oauth-setup.md) | [→ Notion Setup](docs/integrations/NOTION_SETUP.md) | [→ Confluence Setup](docs/integrations/CONFLUENCE_SETUP.md) | [→ Slack Setup](docs/integrations/SLACK_USER_PROXY_SETUP.md)

### ⚡ Performance & Security
- **Near-Instant Startup** — syncs agents and skills once per day; subsequent launches skip all network checks and start in ~100ms
- **Simplified Architecture** with ~3,700 lines removed for better performance
- **Enhanced Security** with comprehensive input validation
- **Intelligent Caching** with hash-based invalidation and TTL-gated sync
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

# Force sync agents/skills from GitHub (overrides 24-hour TTL)
claude-mpm --force-sync

# Skip sync for maximum startup speed
claude-mpm --no-sync

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

**💡 Startup Performance**: Claude MPM syncs agents and skills once per day. Subsequent launches are near-instant (~100ms). Use `--force-sync` to pull the latest content immediately or set `CLAUDE_MPM_SYNC_TTL` (seconds) to customize the sync interval.

**💡 Update Checking**: Claude MPM automatically checks for updates and verifies Claude Code compatibility on startup. Configure in `~/.claude-mpm/configuration.yaml` or see [docs/update-checking.md](docs/update-checking.md).

[→ Complete usage examples: User Guide](docs/user/user-guide.md)

---

## SDK Runtime Mode (Experimental)

**New in v5.11.0** -- Claude MPM can now run the PM agent via the [Claude Agent SDK](https://docs.anthropic.com/en/docs/claude-code/sdk) instead of spawning a CLI subprocess. This enables programmatic control, real-time event streaming, and live session observability.

> **Backward Compatible**: The default runtime is still CLI mode. Existing users do not need to change anything.

### Enabling SDK Mode

```bash
# Via CLI flag
claude-mpm run --sdk

# Via environment variable
export CLAUDE_MPM_RUNTIME=sdk
claude-mpm run

# Force CLI mode explicitly (useful to override auto-detection)
claude-mpm run --cli
```

**Auto-detection**: If the `claude-agent-sdk` Python package is installed and no flag or env var is set, SDK mode is selected automatically. Otherwise, CLI mode is used as the fallback.

### New CLI Flags

| Flag | Description |
|------|-------------|
| `--sdk` | Use Agent SDK runtime (requires `claude-agent-sdk`) |
| `--cli` | Force CLI subprocess runtime |
| `--inject-port <PORT>` | Start message injection endpoint on PORT (default: 7856) |

**Environment variable**: `CLAUDE_MPM_RUNTIME=sdk` or `CLAUDE_MPM_RUNTIME=cli`

### Key Capabilities

**Monitor Agent** -- A background watchdog thread that monitors PM session health:
- Context pressure warnings at configurable thresholds (70%, 80%, 90%, 95%)
- Session duration and idle/stuck detection
- Automatic warnings injected via the hook event bus

**Message Injection** -- External systems can send prompts to the running PM session:
```bash
# Start the injection endpoint
claude-mpm run --sdk --inject-port 7856

# From another terminal or script
curl -X POST http://localhost:7856/inject \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Check the status of PR #123"}'
```

The `/mpm-message` slash command also bridges messages to the PM session via the monitor agent's `systemMessage` channel.

**Session Observability** -- Live session state and activity feed via HTTP:
```bash
# Current session state (idle, processing, tool_call, etc.)
curl http://localhost:7856/session

# Recent activity feed
curl http://localhost:7856/activity
```

### Architecture Overview

The SDK runtime is built on an adapter pattern with clean separation of concerns:

- **`AgentRuntime` ABC** -- Runtime-agnostic interface with `run()`, `resume()`, `fork()`, and `run_with_hooks()` methods
- **`SDKAgentRunner`** -- In-process SDK implementation using `claude-agent-sdk`
- **`CLIAgentRunner`** -- Subprocess adapter wrapping the existing `ClaudeAdapter`
- **`create_runtime()` factory** -- Instantiates the correct backend based on config
- **`RuntimeConfig`** -- Resolves runtime type from `CLAUDE_MPM_RUNTIME` env var or auto-detection
- **`HookEventBus`** -- File-based message queue for sidecar agent to PM communication
- **`SDKEventBridge`** -- Translates SDK events into MPM monitoring dashboard emissions
- **`SessionStateTracker`** -- Thread-safe state machine for session observability

```
                  ┌─────────────────┐
                  │  create_runtime │
                  └────────┬────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
     ┌────────▼────────┐      ┌────────▼────────┐
     │  SDKAgentRunner  │      │  CLIAgentRunner  │
     │  (in-process)    │      │  (subprocess)    │
     └────────┬────────┘      └─────────────────┘
              │
   ┌──────────┼──────────┐
   │          │          │
   ▼          ▼          ▼
Monitor    EventBridge  StateTracker
Agent      (SocketIO)   (/session)
```

### Requirements

- **`claude-agent-sdk`** Python package (optional -- only needed for SDK mode)
- SDK mode is experimental and may change in future releases

---

## What's New in v6.0

**Released in v6.0:**
- ✅ Binary consolidation
- ✅ Auto-migration of `.mcp.json` configs
- ✅ Plugin install and uninstall
- ✅ Stop hook stale count fix
- ✅ Agent workflow end-to-end

### Plugin System (NEW)

Claude MPM can now be installed as a **Claude Code plugin** — no pip install required for core functionality:

```bash
claude plugin marketplace add bobmatnyc/claude-mpm-marketplace
claude plugin install claude-mpm@claude-mpm-marketplace
```

The plugin provides **6 hook events**, **56 skills**, **2 slash commands** (`/mpm-status`, `/mpm-help`), and **MCP server configuration**. For the full CLI, agents, monitor, and dashboard, a pip install is still needed.

### Binary Consolidation (BREAKING)

10 standalone binaries have been consolidated to **2**:

| Binary | Purpose |
|--------|---------|
| `claude-mpm` | All CLI commands + `mcp serve <name>` for MCP servers |
| `claude-hook` | Hook handler (performance-critical, stays separate) |

**Removed standalone binaries**: `claude-mpm-doctor`, `claude-mpm-monitor`, `claude-mpm-socketio`, `claude-mpm-ui`, `confluence-mcp`, `notion-mpm`, `mpm-session-server`, `mpm-session-server-http`

The new `claude-mpm mcp serve <name>` subcommand replaces direct binary invocations. For example:
```bash
# Before (v5.x)
mpm-session-server --port 8080

# After (v6.0)
claude-mpm mcp serve session --port 8080
```

### Auto-Migration

Run `claude-mpm migrate` to automatically update old `.mcp.json` configurations to the new binary names. Migration also runs automatically on startup.

### 56 Bundled Skills

The skills library has grown from 44 to **56 bundled skills**, covering additional development patterns and workflows.

---

## Migration from v5.x

If you are upgrading from v5.x, follow these steps:

1. **Update the package**:
   ```bash
   uv tool install "claude-mpm[monitor,data-processing]" --python 3.13 --force
   ```

2. **Run the migration command** to update `.mcp.json` and other configs:
   ```bash
   claude-mpm migrate
   ```
   This rewrites references to removed binaries (e.g., `mpm-session-server` becomes `claude-mpm mcp serve session`). The migration also runs automatically on startup.

3. **Install the plugin** (optional but recommended):
   ```bash
   claude plugin marketplace add bobmatnyc/claude-mpm-marketplace
   claude plugin install claude-mpm@claude-mpm-marketplace
   ```

4. **Backward compatibility**: `claude-mpm-doctor` still works but prints a deprecation warning. Use `claude-mpm doctor` instead. All other removed binaries require updating to `claude-mpm mcp serve <name>`.

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

## Strategic Direction: Delegated Automation & Cloud Dev Environments

Claude MPM is moving beyond local orchestration toward being the **control plane for delegated agentic automation** — where the PM spawns and manages Claude Code instances running in cloud dev environments rather than only on the local machine.

### The Vision

Today, claude-mpm runs everything on your local machine. The next evolution: the PM stays as a lightweight controller while heavy implementation work is delegated to **cloud-hosted Claude Code agents** with isolated workspaces, full repo access, test runners, and deployment tools.

Each agent gets its own ephemeral environment (a GitHub Codespace, a Gitpod workspace, a remote Docker container, a CI runner) — pre-configured, disposable, and purpose-built for the task.

### Foundation: What's Already Built

The pieces are in place:

| Capability | How It's Used |
|-----------|--------------|
| **SDK mode** (`--sdk`) | Runs Claude programmatically without a local terminal — the bridge to headless/remote execution |
| **Channel Hub** (`--channels`) | Multi-session message bus connecting the local PM to agent sessions |
| **GitHub first-class context** | Automatic PR/branch/repo state injection — cloud agents understand the codebase on arrival |
| **MCP server auto-detection** | Agents discover available tools at session start, no manual configuration |

### Phase 5+: Cloud Dev Sled Integration

The next major phases build on the channel hub:

**Phase 5 — Remote Channel Adapters**: Telegram and Slack adapters connect the PM to agents running anywhere. A message sent to the PM via Slack routes to the correct cloud agent session and streams the response back.

**Phase 6 — Cloud Sled Launch**: The PM can provision an ephemeral cloud dev environment (Codespaces, Gitpod, Daytona, remote container), launch Claude Code in SDK mode inside it, and register the session with the local Channel Hub. The PM delegates a task; the cloud agent does the work; results flow back through the channel.

**Phase 7 — Fleet Coordination**: Multiple cloud agents working in parallel on independent tasks, coordinated by the local PM. The PM owns task routing, progress tracking, and result aggregation. Individual agents are disposable — the PM is the persistent state.

### Design Principles

- **Local PM, remote workers**: The controller stays lightweight and local. Execution scales out to cloud environments.
- **Channels as the backbone**: The Channel Hub (already built) is the messaging layer that connects PM to remote agents — no new protocol needed.
- **GitHub-native by default**: Cloud agents start with full repo context automatically. No setup required per task.
- **SDK mode is the execution primitive**: All remote agent execution goes through `--sdk`. The programmatic API is stable and already supports headless operation.
- **Ephemeral environments, persistent coordination**: Cloud workspaces are created and destroyed per task. The PM's session state and task history persist locally.

### Near-Term Milestones (Phase 4)

Before cloud sled work begins, Phase 4 completes the channel hub foundation:

1. Telegram and Slack adapters (channel hub variants)
2. Hub-CLI IPC bridge (`channels list`, `channels auth` talk to running hub)
3. GitHub context injection in plain `--sdk` mode (not just channels mode)
4. Test coverage for the channels and GitHub service layers

See [`docs/research/multi-channel-github-phase4-analysis-2026-03-26.md`](docs/research/multi-channel-github-phase4-analysis-2026-03-26.md) for the detailed Phase 4 analysis.

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
claude-mpm setup gworkspace-mcp         # Canonical name (preferred)
claude-mpm setup google-workspace-mcp   # Legacy alias (also works)
claude-mpm setup slack-mpm
claude-mpm setup notion
claude-mpm setup confluence

# Setup multiple at once
claude-mpm setup kuzu-memory mcp-vector-search gworkspace-mcp
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
