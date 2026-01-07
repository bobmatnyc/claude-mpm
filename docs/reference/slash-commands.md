# Claude MPM Slash Commands Reference

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This document provides a comprehensive reference for all Claude MPM slash commands, organized by category with enhanced naming for better discoverability and future hierarchical namespace support.

## What's New ✨

**Unified Configuration Interface**: All agent and skill management has been consolidated into `/mpm-configure`:

- **`/mpm-configure`** - Interactive configuration menu for agents, skills, and project settings
  - Toolchain detection
  - Agent recommendations
  - Skills management
  - Auto-configuration

**Quick Start**:
```bash
# Interactive configuration menu
/mpm-configure
```

**Learn More**:
- [Auto-Configuration User Guide](../getting-started/auto-configuration.md) - Complete documentation
- [Agent Presets Guide](../user/agent-presets.md) - Alternative approach for standard stacks

---

## Command Naming Convention

Claude MPM uses an enhanced flat naming scheme that prepares for future hierarchical namespaces:

- **Current Format**: `/mpm-{category}-{action}` (e.g., `/mpm-agents-list`)
- **Future Format**: `/mpm/{category}:{action}` (when Claude Code supports hierarchical namespaces)
- **Backward Compatibility**: Old command names remain available with deprecation warnings

### Command Categories

1. **Agents** (`mpm/agents`) - Agent management and auto-configuration ✨ Enhanced in v5.0
2. **Config** (`mpm/config`) - Configuration viewing and validation
3. **Tickets** (`mpm/ticket`) - Ticketing workflows and organization
4. **Session** (`mpm/session`) - Session management and resumption
5. **System** (`mpm/system`) - System commands (diagnostics, help, init, etc.)

## Agents Category

Commands for managing Claude MPM agents, including detection, recommendations, and auto-configuration.

### `/mpm-configure`

**Future**: `/mpm/config:interactive`
**Description**: Unified interactive configuration interface for agents, skills, and project settings

**Usage**:
```bash
/mpm-configure
```

**What it provides**:
- **Interactive Menu**: Navigate through configuration options
- **Toolchain Detection**: Scan project for languages, frameworks, and tools
- **Agent Recommendations**: Get intelligent agent suggestions based on your stack
- **Skills Management**: Deploy and manage Claude Code skills
- **Auto-Configuration**: Automatic setup with intelligent defaults

**Main Menu Options**:
1. **Detect Toolchain** - Scan project technologies
2. **View Recommendations** - See suggested agents and skills
3. **Deploy Agents** - Install recommended agents
4. **Manage Skills** - Deploy and configure skills
5. **Configuration Settings** - View and modify settings

**When to use**:
- First-time setup of a new project
- Adding Claude MPM to existing project
- Managing agents and skills configuration
- Reviewing project toolchain and recommendations
- Standardizing team environments

**Example Interaction**:
```
🔧 Claude MPM Configuration

Select an option:
1. Detect Project Toolchain
2. View Agent Recommendations
3. Deploy Agents
4. Manage Skills
5. View Configuration
6. Exit

Choice [1-6]: 1

🔍 Detecting project stack...
  ✓ Found: Python 3.11, FastAPI 0.104, React 18.2
  ✓ 8 essential agents recommended
  ✓ 3 recommended agents

What would you like to do?
```

**See Also**:
- **User Guide**: [Auto-Configuration Guide](../getting-started/auto-configuration.md) - Complete workflow documentation
- **User Guide**: [Agent Presets Guide](../user/agent-presets.md) - Alternative preset approach
- **CLI Reference**: [Configuration Management](cli-agents.md) - Command-line usage

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

### `/mpm-organize`

**Future**: `/mpm/system:organize`
**Description**: Organize project files into proper directories with intelligent pattern detection

**Usage**:
```bash
/mpm-organize [options]
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
| `/mpm-agents` | `/mpm-agents-list` | Deprecated in v5.x, removed in v5.1.0 |
| `/mpm-auto-configure` | `/mpm-agents-auto-configure` | Deprecated in v5.x, removed in v5.1.0 |
| `/mpm-config` | `/mpm-config-view` | Deprecated in v5.x, removed in v5.1.0 |
| `/mpm-ticket` | `/mpm-ticket-view` | Deprecated in v5.x, removed in v5.1.0 |
| `/mpm-resume` | `/mpm-session-resume` | Deprecated in v5.x, removed in v5.1.0 |

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

### New in v5.0

- **[Auto-Configuration User Guide](../getting-started/auto-configuration.md)** - Complete guide to auto-configuration features
- **[Agent Presets Guide](../user/agent-presets.md)** - Pre-configured agent bundles for common stacks
- **[CLI Agents Reference](cli-agents.md)** - Command-line interface for agent management

### User Guides

- **[Getting Started](../getting-started/)** - First steps with Claude MPM
- **[Agent Sources Guide](../user/agent-sources.md)** - Managing agent repositories
- **[User Guide](../user/user-guide.md)** - Complete user documentation
- **[Troubleshooting](../user/troubleshooting.md)** - Common issues and solutions

### Reference Documentation

- **[Agent Capabilities Reference](../agents/agent-capabilities-reference.md)** - Detailed agent descriptions
- **[Configuration Reference](../configuration/reference.md)** - Configuration file format

### Implementation

- **Hierarchical Namespace Analysis**: Archived research (see `docs/_archive/`)

---

**Last Updated**: 2025-11-29
**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata
**Status**: Phase 1 Complete - Hierarchical directories deferred pending Claude Code fix
