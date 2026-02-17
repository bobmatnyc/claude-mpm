# Claude MPM Documentation

Claude MPM extends Claude Code CLI with multi-agent workflows, persistent memory, and real-time monitoring.

## Quick Start

```bash
# 1. Install
pipx install "claude-mpm[monitor]"

# 2. Auto-configure your project
claude-mpm auto-configure

# 3. Run
claude-mpm run --monitor
```

## Documentation Index

### Getting Started
- **[Installation](getting-started/installation.md)** - Installation instructions
- **[Quick Start](getting-started/quick-start.md)** - Get up and running quickly
- **[Auto-Configuration](getting-started/auto-configuration.md)** - Automatic project configuration
- **[Absolute Beginners Guide](getting-started/absolute-beginners-guide.md)** - Step-by-step guide for new users
- **[Incremental Pause Quickstart](getting-started/incremental-pause-quickstart.md)** - Quick guide for incremental workflows
- **[Version Policy](getting-started/VERSION_POLICY.md)** - Versioning and compatibility policy

### Integrations
- **[Slack Setup](integrations/SLACK_SETUP.md)** - Integrate with Slack
- **[Slack Setup Guide](integrations/slack-setup.md)** - Detailed Slack configuration
- **[Slack User Proxy Setup](integrations/SLACK_USER_PROXY_SETUP.md)** - User proxy configuration for Slack
- **[MCP Session Server](integrations/mcp-session-server.md)** - Programmatic session management via MCP

### Features

#### Delegation
- **[Delegation Detector](features/delegation/delegation-detector.md)** - Delegation detection system
- **[Delegation Detector Hook](features/delegation/delegation-detector-hook.md)** - Hook implementation
- **[Delegation Hook Summary](features/delegation/delegation-hook-summary.md)** - Summary of delegation hooks

#### Other Features
- **[Incremental Pause Workflow](features/incremental-pause-workflow.md)** - Workflow for incremental development
- **[AutoTodos Architecture](features/autotodos-architecture.md)** - Architecture of AutoTodos feature
- **[AutoTodos](features/autotodos.md)** - AutoTodos feature overview
- **[Startup Migrations](features/startup-migrations.md)** - Startup migration handling
- **[Tasklist Session Integration](features/tasklist-session-integration.md)** - Session integration

### Architecture
- **[Overview](architecture/overview.md)** - Architecture overview
- **[Single-Tier Design](architecture/single-tier-design.md)** - Single-tier architecture
- **[Simplified Deployment Model](architecture/simplified-deployment-model.md)** - Deployment architecture
- **[Dependency Injection](architecture/dependency-injection.md)** - DI patterns
- **[Monitor Server Architecture](architecture/monitor-server-architecture.md)** - Monitor server design
- **[Network Ports Configuration](architecture/NETWORK_PORTS_CONFIGURATION.md)** - Port configuration
- **[AutoTodos Architecture Fix](architecture/autotodos-architecture-fix.md)** - Architecture fixes
- **[Memory Flow](architecture/memory-flow.md)** - Memory system flow
- **[Skills vs Commands](architecture/skills-vs-commands-clarification.md)** - Terminology clarification

### Development
- **[Documentation Standards](development/DOCUMENTATION-STANDARDS.md)** - Documentation guidelines
- **[Documentation Audit](development/DOCUMENTATION-AUDIT.md)** - Documentation audit results
- **[Agent Skills Spec Implementation](development/agentskills-spec-implementation.md)** - Skills specification
- **[Dashboard File Tree Enhancements](development/DASHBOARD_FILE_TREE_ENHANCEMENTS.md)** - Dashboard improvements

### Developer Reference
- **[Startup Procedures](developer/startup/STARTUP-PROCEDURES.md)** - Complete initialization sequence
- **[Tools Framework Guide](developer/tools-framework-guide.md)** - Tool development guide
- **[Token Usage Verification](developer/token-usage-verification-findings.md)** - Token usage analysis

### User Guide
- **[User Guide](user/user-guide.md)** - Complete user documentation
- **[Troubleshooting](user/troubleshooting.md)** - Common issues and solutions

### Guides
- **[Prompting Guide](guides/prompting-guide.md)** - How to write effective prompts
- **[Prompt Examples Library](guides/prompt-examples.md)** - Example prompts
- **[OAuth Setup](guides/oauth-setup.md)** - OAuth configuration
- **[FAQ](guides/FAQ.md)** - Frequently asked questions
- **[All Guides](guides/README.md)** - Complete guides index

### Reference
- **[API Overview](reference/api-overview.md)** - API documentation
- **[CLI Reference](reference/cli-agents.md)** - CLI commands
- **[Slash Commands](reference/slash-commands.md)** - In-session commands
- **[All Reference Docs](reference/README.md)** - Complete reference index

### Agents
- **[Agent System](agents/README.md)** - Agent system overview
- **[Creating Agents](agents/creating-agents.md)** - How to create custom agents

### Developers
- **[Developer Docs](developer/README.md)** - Developer documentation
- **[Architecture](architecture/overview.md)** - Technical architecture
- **[Design](design/README.md)** - Design decisions

## Getting Help

- **Troubleshooting**: [user/troubleshooting.md](user/troubleshooting.md)
- **Diagnostics**: Run `claude-mpm doctor`
- **Issues**: Report bugs or request features on GitHub

---

If you are new, start with [Getting Started](getting-started/README.md).
