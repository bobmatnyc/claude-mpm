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

### For Users
- **[Getting Started](user/getting-started.md)** - Installation, setup, and first steps
- **[User Guide](user/user-guide.md)** - Features, workflows, and best practices
- **[Resume Log System](user/resume-logs.md)** - Proactive context management guide
- **[Configuration Reference](configuration.md)** - Complete configuration options
- **[Troubleshooting](user/troubleshooting.md)** - Common issues and solutions

### For Developers
- **[Architecture](developer/ARCHITECTURE.md)** - System design and core concepts
- **[Resume Log Architecture](developer/resume-log-architecture.md)** - Technical implementation details
- **[Extending](developer/extending.md)** - Build custom agents, hooks, and services
- **[API Reference](developer/api-reference.md)** - Complete API documentation

### For Agent Creators
- **[PM Workflow](agents/pm-workflow.md)** - Project Manager agent patterns
- **[Agent Patterns](agents/agent-patterns.md)** - Creating effective agents
- **[Creating Agents](agents/creating-agents.md)** - Step-by-step agent development

### Examples & Tutorials
- **[Resume Log Examples](examples/resume-log-examples.md)** - Real-world resume log workflows and tutorials

## Key Features

**Auto-Configuration (v4.10.0+)**: Automatic stack detection and agent deployment
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

**Local Process Management (v4.13.0+)**: Professional-grade local deployment
- Three-tier health checks (HTTP, process, resource)
- Auto-restart with exponential backoff
- Memory leak detection and circuit breaker
- Configuration-driven via YAML

**Resume Log System (v4.17.2)**: Proactive context management
- Graduated thresholds at 70%/85%/95% (60k token buffer)
- Automatic 10k-token structured logs for session continuity
- Seamless resumption with full context preservation
- Zero-configuration automatic operation

**Session Management**: Pause and resume with full context
- Save state with `claude-mpm mpm-init pause`
- Resume with `claude-mpm mpm-init resume`
- Automatic change detection

**Real-Time Monitoring**: Live dashboard shows agent collaboration
- WebSocket-based updates
- Agent activity tracking
- Performance metrics

**Performance (v4.8.2+)**: 91% latency reduction in hook system
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

**Quick Tip**: Start with [user/getting-started.md](user/getting-started.md) if you're new, or jump to [developer/architecture.md](developer/architecture.md) for system internals.
