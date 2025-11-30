# Claude MPM Slash Commands Reference

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This document provides a comprehensive reference for all Claude MPM slash commands, organized by category with enhanced naming for better discoverability and future hierarchical namespace support.

## Command Naming Convention

Claude MPM uses an enhanced flat naming scheme that prepares for future hierarchical namespaces:

- **Current Format**: `/mpm-{category}-{action}` (e.g., `/mpm-agents-list`)
- **Future Format**: `/mpm/{category}:{action}` (when Claude Code supports hierarchical namespaces)
- **Backward Compatibility**: Old command names remain available with deprecation warnings

### Command Categories

1. **Agents** (`mpm/agents`) - Agent management and auto-configuration
2. **Config** (`mpm/config`) - Configuration viewing and validation
3. **Tickets** (`mpm/ticket`) - Ticketing workflows and organization
4. **Session** (`mpm/session`) - Session management and resumption
5. **System** (`mpm/system`) - System commands (diagnostics, help, init, etc.)

## Agents Category

Commands for managing Claude MPM agents, including detection, recommendations, and auto-configuration.

### `/mpm-agents-list`

**Aliases**: `/mpm-agents` (deprecated)
**Future**: `/mpm/agents:list`
**Description**: List all available Claude MPM agents with versions and deployment status

**Usage**:
```bash
/mpm-agents-list
```

**What it does**:
- Lists all available agents (built-in and custom)
- Shows deployment status and version information
- Displays agent capabilities and model preferences

**Related**: `/mpm-agents-detect`, `/mpm-agents-recommend`

---

### `/mpm-agents-detect`

**Future**: `/mpm/agents:detect`
**Description**: Scan project to detect programming languages, frameworks, tools, and configurations

**Usage**:
```bash
/mpm-agents-detect
```

**What it detects**:
- Programming languages (Python, Node.js, Rust, Go, Java)
- Frameworks (FastAPI, Next.js, React, Express, Django, etc.)
- Testing tools (pytest, Jest, Playwright, Cypress)
- Build tools (Vite, Webpack, Rollup, esbuild)
- Deployment configurations (Docker, Vercel, Railway, PM2)

**Output**: Comprehensive toolchain summary with detected versions

---

### `/mpm-agents-recommend`

**Future**: `/mpm/agents:recommend`
**Description**: Get intelligent agent recommendations based on detected project toolchain

**Usage**:
```bash
/mpm-agents-recommend
```

**What it provides**:
- **Essential agents**: Core agents required for your stack
- **Recommended agents**: Complementary agents for full functionality
- **Optional agents**: Specialized agents for detected tools
- **Rationale**: Explanation for each recommendation

**Related**: `/mpm-agents-detect`, `/mpm-agents-auto-configure`

---

### `/mpm-agents-auto-configure`

**Aliases**: `/mpm-auto-configure` (deprecated)
**Future**: `/mpm/agents:auto-configure`
**Description**: Automatically detect project toolchain and configure appropriate agents

**Usage**:
```bash
/mpm-agents-auto-configure [options]
```

**Options**:
- `--preview` - Show what would be configured without making changes
- `--yes` - Automatically apply recommendations without prompting
- `--force` - Force reconfiguration even if agents already deployed

**Workflow**:
1. Detect project toolchain
2. Generate agent recommendations
3. Deploy recommended agents (with confirmation)

**Related**: `/mpm-agents-detect`, `/mpm-agents-recommend`

---

## Config Category

Commands for viewing and validating Claude MPM configuration.

### `/mpm-config-view`

**Aliases**: `/mpm-config` (deprecated)
**Future**: `/mpm/config:view`
**Description**: View and validate Claude MPM configuration settings

**Usage**:
```bash
/mpm-config-view [subcommand] [options]
```

**What it shows**:
- Current configuration settings
- Agent deployment status
- Configuration file locations
- Validation status

---

## Tickets Category

Commands for ticketing workflows and project organization.

### `/mpm-ticket-organize`

**Aliases**: `/mpm-organize` (deprecated)
**Future**: `/mpm/ticket:organize`
**Description**: Organize project files into proper directories with intelligent pattern detection

**Usage**:
```bash
/mpm-ticket-organize [options]
```

**Options**:
- `--dry-run` - Preview changes without applying
- `--force` - Proceed even with uncommitted changes
- `--interactive` - Interactive mode with preview

**What it does**:
- Detects misplaced files based on framework conventions
- Suggests proper directory structure
- Moves files with git-awareness
- Preserves project organization patterns

---

### `/mpm-ticket-view`

**Aliases**: `/mpm-ticket` (deprecated)
**Future**: `/mpm/ticket:view`
**Description**: Orchestrate ticketing agent for comprehensive project management workflows

**Usage**:
```bash
/mpm-ticket-view <subcommand> [options]
```

**Workflows supported**:
- Ticket creation and management
- Epic and milestone planning
- Sprint organization
- Dependency tracking

---

## Session Category

Commands for session management and work resumption.

### `/mpm-session-resume`

**Aliases**: `/mpm-resume` (deprecated)
**Future**: `/mpm/session:resume`
**Description**: Load and display context from most recent paused session to continue work

**Usage**:
```bash
/mpm-session-resume
```

**What it loads**:
- Previous session context
- Active tickets and tasks
- File change history
- Agent conversation state

---

## System Category

Core system commands for diagnostics, help, initialization, and monitoring.

### `/mpm-doctor`

**Future**: `/mpm/system:doctor`
**Description**: Run comprehensive diagnostic checks on Claude MPM installation

**Usage**:
```bash
/mpm-doctor
```

**Checks**:
- Installation integrity
- Configuration validity
- Agent deployment status
- Dependency availability
- Permission issues

---

### `/mpm-help`

**Future**: `/mpm/system:help`
**Description**: Display help information for Claude MPM slash commands and CLI capabilities

**Usage**:
```bash
/mpm-help [command]
```

---

### `/mpm-init`

**Future**: `/mpm/system:init`
**Description**: Initialize or update project for Claude Code and Claude MPM

**Usage**:
```bash
/mpm-init [update]
```

**What it does**:
- Creates `.claude-mpm/` directory structure
- Initializes configuration files
- Deploys default agents
- Sets up project for optimal Claude Code usage

---

### `/mpm-monitor`

**Future**: `/mpm/system:monitor`
**Description**: Control Claude MPM monitoring server for real-time dashboard interface

**Usage**:
```bash
/mpm-monitor [start|stop|status]
```

---

### `/mpm-status`

**Future**: `/mpm/system:status`
**Description**: Display Claude MPM status including environment, services, and health

**Usage**:
```bash
/mpm-status
```

---

### `/mpm-version`

**Future**: `/mpm/system:version`
**Description**: Show comprehensive version information for Claude MPM

**Usage**:
```bash
/mpm-version
```

**Output**:
- Claude MPM version
- Installed agents and versions
- Skills versions
- System dependencies

---

### `/mpm`

**Future**: `/mpm`
**Description**: Access Claude MPM functionality and manage multi-agent orchestration

**Usage**:
```bash
/mpm
```

Main entry point for Claude MPM. Shows overview of available commands.

---

## YAML Frontmatter Metadata

All command files include YAML frontmatter for namespace metadata. This enables:

- **Current**: Enhanced naming and categorization
- **Future**: Automatic migration to hierarchical namespaces when Claude Code supports them

### Frontmatter Schema

```yaml
---
namespace: mpm/category        # Logical namespace (e.g., "mpm/agents")
command: action                # Command name within namespace (e.g., "list")
aliases: [alias1, alias2]      # Alternative command names
migration_target: /path        # Future hierarchical command path
category: category_name        # Category (agents, config, tickets, session, system)
deprecated_aliases: []         # Old names being phased out
description: Brief description # One-line command description
---
```

### Valid Categories

- `agents` - Agent management commands
- `config` - Configuration commands
- `tickets` - Ticketing and organization commands
- `session` - Session management commands
- `system` - System and diagnostic commands

---

## Migration Guide

### From Deprecated Commands

If you're using deprecated command names, here's how to migrate:

| Old Command | New Command | Migration Timeline |
|-------------|-------------|-------------------|
| `/mpm-agents` | `/mpm-agents-list` | Deprecated in v4.27.0, removed in v5.1.0 |
| `/mpm-auto-configure` | `/mpm-agents-auto-configure` | Deprecated in v4.27.0, removed in v5.1.0 |
| `/mpm-config` | `/mpm-config-view` | Deprecated in v4.27.0, removed in v5.1.0 |
| `/mpm-organize` | `/mpm-ticket-organize` | Deprecated in v4.27.0, removed in v5.1.0 |
| `/mpm-ticket` | `/mpm-ticket-view` | Deprecated in v4.27.0, removed in v5.1.0 |
| `/mpm-resume` | `/mpm-session-resume` | Deprecated in v4.27.0, removed in v5.1.0 |

### Future Hierarchical Migration

When Claude Code [issue #2422](https://github.com/anthropics/claude-code/issues/2422) is resolved, commands will automatically migrate to hierarchical format:

- `/mpm-agents-list` → `/mpm/agents:list`
- `/mpm-config-view` → `/mpm/config:view`
- `/mpm-ticket-organize` → `/mpm/ticket:organize`

Claude MPM will handle this migration automatically with backward-compatible aliases.

---

## Command Deployment

All slash commands are deployed from `src/claude_mpm/commands/` to `~/.claude/commands/` during installation or when running:

```bash
claude-mpm commands deploy --force
```

### Validation

Commands are validated during deployment:
- YAML frontmatter syntax
- Required fields presence
- Category validity
- Data type correctness

Validation warnings are logged but don't block deployment.

---

## Related Documentation

- [Research: Hierarchical Namespace Analysis](../research/slash-command-hierarchical-namespace-analysis-2025-11-29.md)
- [Agent Capabilities Reference](../agents/agent-capabilities-reference.md)
- [User Guide](../user/user-guide.md)

---

**Last Updated**: 2025-11-29
**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata
**Status**: Phase 1 Complete - Hierarchical directories deferred pending Claude Code fix
