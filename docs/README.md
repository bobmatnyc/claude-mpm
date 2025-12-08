# Claude MPM Documentation

**Version 4.17.2** | Claude Multi-Agent Project Manager

Welcome to Claude MPM - a powerful orchestration framework that extends Claude Code with multi-agent workflows, persistent memory, and real-time monitoring.

## Table of Contents

- [Quick Start](#quick-start)
- [Documentation](#documentation)
- [Key Features](#key-features)
- [Getting Help](#getting-help)

## Quick Start

```bash
# 1. Install
pipx install "claude-mpm[monitor]"

# 2. Auto-configure your project
claude-mpm auto-configure

# 3. Run
claude-mpm run --monitor
```

That's it! Auto-configuration detects your project's stack and deploys the right agents automatically.

## Documentation

### 🚀 Getting Started
- **[Installation](getting-started/installation.md)** - Install Claude MPM and Claude Code CLI
- **[Quick Start](getting-started/quick-start.md)** - Get running in 5 minutes
- **[Auto-Configuration](getting-started/auto-configuration.md)** - Automatic project setup and agent deployment

### 👥 For Users
- **[User Guide](user/user-guide.md)** - Features, workflows, and best practices
- **[Resume Log System](user/resume-logs.md)** - Proactive context management guide
- **[Troubleshooting](user/troubleshooting.md)** - Common issues and solutions
- **[FAQ](guides/FAQ.md)** - Frequently asked questions

### 📖 Guides & How-To
- **[Single-Tier Agent System](guides/single-tier-agent-system.md)** - Git-based agent management (NEW in v5.0)
- **[Monitoring](guides/monitoring.md)** - Real-time agent monitoring
- **[Ticketing Workflows](guides/ticketing-workflows.md)** - Project management integration

### 🔧 Configuration & Deployment
- **[Configuration Reference](configuration/reference.md)** - Complete configuration options
- **[Deployment Overview](deployment/overview.md)** - Deployment strategies and operations

### 🏗️ Architecture & Design
- **[Architecture Overview](architecture/overview.md)** - High-level system design
- **[Single-Tier Design](architecture/single-tier-design.md)** - Agent system architecture (NEW in v5.0)
- **[Design Decisions](design/)** - Feature designs and rationale

### 🤖 Agent System
- **[Agent Overview](reference/agents-overview.md)** - Multi-agent orchestration concepts
- **[PM Workflow](agents/pm-workflow.md)** - Project Manager agent patterns
- **[Agent Patterns](agents/agent-patterns.md)** - Creating effective agents
- **[Creating Agents](agents/creating-agents.md)** - Step-by-step agent development

### 🔍 Reference
- **[API Reference](reference/api-overview.md)** - Complete API documentation
- **[CLI Reference](reference/cli-agents.md)** - Command-line interface
- **[Agent Sources API](reference/agent-sources-api.md)** - Technical API reference (NEW in v5.0)

### 🛠️ For Developers
- **[Developer Architecture](developer/ARCHITECTURE.md)** - System design and core concepts
- **[Extending](developer/extending.md)** - Build custom agents, hooks, and services
- **[Contributing](developer/)** - Development setup and contribution guidelines

### Examples & Tutorials
- **[Resume Log Examples](examples/resume-log-examples.md)** - Real-world resume log workflows and tutorials

## Key Features

**Auto-Configuration**: Automatic stack detection and agent deployment (since v4.10.0)
- Detects Python, Node.js, Rust, Go, and more
- Identifies frameworks (FastAPI, Next.js, React, etc.)
- Recommends agents with confidence scores (80%+ default)

**Multi-Agent System**: 15+ specialized agents for comprehensive project management
- Project Manager (PM) orchestrates workflow
- Research, Engineer, QA, Documentation specialists
- Language-specific coding agents (Python, TypeScript, Go, Rust, etc.)

**Agent Memory**: Persistent learning with JSON response fields
- Project-specific knowledge graphs
- Cross-session learning and context
- Automatic context enrichment

**Local Process Management**: Professional-grade local deployment (since v4.13.0)
- Three-tier health checks (HTTP, process, resource)
- Auto-restart with exponential backoff
- Memory leak detection and circuit breaker
- Configuration-driven via YAML

**Resume Log System**: Proactive context management (since v4.17.2)
- Graduated thresholds at 70%/85%/95% (60k token buffer)
- Automatic 10k-token structured logs for session continuity
- Seamless resumption with full context preservation
- Zero-configuration automatic operation

**Session Management**: Automatic saving and manual pause/resume with full context
- **NEW**: Auto-save every 5 minutes (configurable 60-1800s)
- Graceful shutdown with final save - no data loss
- Manual pause: `claude-mpm mpm-init pause`
- Resume: `claude-mpm mpm-init resume`
- Automatic change detection

**Real-Time Monitoring**: Live dashboard shows agent collaboration
- WebSocket-based updates
- Agent activity tracking
- Performance metrics

**Performance**: 91% latency reduction in hook system (since v4.8.2)
- Git branch caching with 5-minute TTL
- Non-blocking HTTP fallback
- 50-80% overall improvement

**Security**: Comprehensive input validation and filesystem restrictions

**Service-Oriented**: Five specialized service domains with clear contracts

## Getting Help

1. **Quick Reference**: Use the documentation links above
2. **Troubleshooting**: Check [user/troubleshooting.md](user/troubleshooting.md)
3. **GitHub Issues**: Report bugs or request features
4. **API Docs**: See [developer/api-reference.md](developer/api-reference.md)

---

**Quick Tip**: Start with [Getting Started](getting-started/) if you're new, or jump to [Architecture](architecture/overview.md) for system internals.
