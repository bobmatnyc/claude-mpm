# User Documentation

Quick navigation for Claude MPM users.

## 🌟 What's New in v5.x

**Git-First Agent Architecture** - Agents are now sourced from Git repositories by default:
- ✅ **Automatic Updates**: Agents sync from GitHub on startup
- ✅ **Version Control**: Track agent changes through Git history
- ✅ **Bandwidth Efficient**: ETag-based caching reduces network usage by 95%+
- ✅ **Multi-Repository**: Support multiple agent sources with priority-based resolution

**See**: [Agent Sources Guide](agent-sources.md) and [Migration Guide](../migration/agent-sources-git-default-v4.5.0.md) (historical)

## Documentation Files

- **[User Guide](user-guide.md)** - Features, workflows, best practices, and advanced usage
  - Includes: `/mpm-ticket` slash command for ticketing workflows
- **[Agent Sources Guide](agent-sources.md)** - Managing Git repositories with agent definitions
- **[Skills Versioning Guide](skills-versioning.md)** - Understanding and using versioned skills
- **[Troubleshooting](troubleshooting.md)** - Common issues, diagnostics, and solutions
  - Includes: Agent source troubleshooting section

## Getting Started

For new users, start with the **[Getting Started](../getting-started/)** section:
- **[Installation](../getting-started/installation.md)** - Install Claude MPM and Claude Code CLI
- **[Quick Start](../getting-started/quick-start.md)** - Get running in 5 minutes
- **[Auto-Configuration](../getting-started/auto-configuration.md)** - Automatic project setup

## Guides

- **[Ticketing Workflows](../guides/ticketing-workflows.md)** - Comprehensive guide to `/mpm-ticket` command
- **[Ticket Scope Protection](../guides/ticket-scope-protection.md)** - Best practices for ticket management

## Quick Links

**First Time Here?**
1. Read [Getting Started](getting-started.md) → Install and run your first task
2. Browse [User Guide](user-guide.md) → Learn key features
3. Keep [Troubleshooting](troubleshooting.md) handy → Solve issues quickly

**Common Tasks**
- Install: See [Getting Started - Installation](getting-started.md#installation)
- **Add agent sources**: See [Agent Sources Guide - Quick Start](agent-sources.md#quick-start)
- **Manage agent repositories**: See [Agent Sources Guide - Managing Agent Sources](agent-sources.md#managing-agent-sources)
- Auto-configure: See [User Guide - Auto-Configuration](user-guide.md#auto-configuration)
- Deploy servers: See [User Guide - Local Process Management](user-guide.md#local-process-management)
- Pause/resume: See [User Guide - Session Management](user-guide.md#session-management)
- Manage tickets: See [User Guide - Ticketing Workflows](user-guide.md#ticketing-workflows) or [Ticketing Workflows Guide](../guides/ticketing-workflows.md)

**Need Help?**
- Check [Troubleshooting](troubleshooting.md) first
- Run `claude-mpm doctor` for diagnostics
- Use `/mpm-doctor` in Claude Code sessions
