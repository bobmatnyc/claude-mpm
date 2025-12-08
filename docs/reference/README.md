# Reference Documentation

Complete reference documentation for Claude MPM systems and architecture.

## 🌟 New in v4.5.0: Git-First Agent Architecture

Claude MPM now uses **git-first architecture** for agent deployment:

- **4-Tier Discovery System**: Local project → Git sources (by priority) → Built-in fallback
- **ETag-Based Caching**: Intelligent HTTP caching reduces bandwidth by 95%+
- **Priority-Based Resolution**: Multiple repositories with configurable precedence
- **Automatic Sync**: Agents update from Git on startup (non-blocking)

**Technical Documentation:**
- [Agent Source Commands CLI Reference](cli-agent-source.md) - Complete command reference
- [Agent Sources API](agent-sources-api.md) - Python API and architecture
- [Migration Guide](../migration/agent-sources-git-default-v4.5.0.md) - Upgrading from v4.4.x

## Available References

- **[Agent Source Commands CLI Reference](cli-agent-source.md)** - ⭐ Complete CLI reference for `agent-source` commands (v4.5.0+)
- **[Agent Sources API](agent-sources-api.md)** - ⭐ Technical API reference for git-first agent system (v4.5.0+)
- **[Doctor Command CLI Reference](cli-doctor.md)** - Complete CLI reference for doctor command
- **[Configuration](../configuration/reference.md)** - Complete configuration reference for Claude MPM
- **[Deployment Guide](DEPLOY.md)** - Complete deployment procedures and release management
- **[Slash Commands Reference](slash-commands.md)** - Complete slash commands reference
- **[Project Structure](STRUCTURE.md)** - Codebase organization and file placement
- **[Services Reference](SERVICES.md)** - Service-oriented architecture details
- **[Memory System](MEMORY.md)** - Memory and context management
- **[Testing & QA](QA.md)** - Testing standards and quality assurance
- **[Skills Quick Reference](skills-quick-reference.md)** - Quick reference for Claude Code skills deployment
- **[Homebrew Troubleshooting](HOMEBREW_UPDATE_TROUBLESHOOTING.md)** - Homebrew tap integration issues
- **[Structured Questions API](structured-questions-api.md)** - Complete API reference for structured questions framework
- **[Structured Questions Templates](structured-questions-templates.md)** - Catalog of available question templates

## Quick Reference

**System Diagnostics:**
- [Doctor Command CLI Reference](cli-doctor.md) - Complete CLI reference (NEW)
- [Doctor Command Guide](../guides/doctor-command.md) - User guide and troubleshooting (NEW)
- [Slash Commands Reference](slash-commands.md) - Complete slash commands reference

**System Architecture:**
- [Services Reference](SERVICES.md) - Five service domains
- [Project Structure](STRUCTURE.md) - Code organization
- [Architecture Overview](../developer/ARCHITECTURE.md) - System design

**Operations:**
- [Configuration](../configuration/reference.md) - Configuration options and settings
- [Deployment Guide](DEPLOY.md) - Release procedures
- [Memory System](MEMORY.md) - Context management
- [Testing Guide](QA.md) - Quality standards
- [Skills Quick Reference](skills-quick-reference.md) - Skills deployment commands

**Skills & Agents:**
- **Git-First Agent Architecture (v4.5.0+):**
  - [Agent Source Commands CLI](cli-agent-source.md) - Complete command reference
  - [Agent Sources API](agent-sources-api.md) - Python API and architecture
  - [Agent Sources User Guide](../user/agent-sources.md) - User guide with examples
  - [Migration Guide](../migration/agent-sources-git-default-v4.5.0.md) - Upgrading from v4.4.x
- **Skills System:**
  - [Skills Quick Reference](skills-quick-reference.md) - Command reference for skill deployment
  - [Research Agent](../agents/research-agent.md) - Skill detection and recommendations
  - [Skills Deployment Guide](../guides/skills-deployment-guide.md) - Comprehensive deployment guide

**Development:**
- [Testing & QA](QA.md) - Testing requirements
- [Code Formatting](../developer/CODE_FORMATTING.md) - Code standards
- [API Reference](../developer/api-reference.md) - API documentation

## Navigation

- **[Developer Documentation](../developer/README.md)** - Complete developer guide
- **[User Documentation](../user/README.md)** - End-user documentation
- **[Documentation Hub](../README.md)** - All documentation

---

**For technical implementation details**: See [Developer Documentation](../developer/README.md)
