# Agent Source Commands CLI Reference

**Command**: `claude-mpm agent-source`
**Category**: Agent Repository Management
**Related Ticket**: [1M-442](https://linear.app/workspace/issue/1M-442)

Complete CLI reference for agent source repository management commands.

## Table of Contents

- [Overview](#overview)
- [Subcommands](#subcommands)
  - [add](#add---add-agent-source)
  - [list](#list---list-agent-sources)
  - [update](#update---sync-agent-sources)
  - [enable](#enable---enable-agent-source)
  - [disable](#disable---disable-agent-source)
  - [show](#show---show-source-details)
  - [remove](#remove---remove-agent-source)
- [Common Options](#common-options)
- [Exit Codes](#exit-codes)
- [Examples](#examples)
- [Related Commands](#related-commands)

## Overview

The `agent-source` command group manages Git repositories containing agent definitions. These commands allow you to:

- Add remote Git repositories as agent sources
- Sync agents from repositories to local cache
- Configure priority for conflict resolution
- Enable/disable sources without removing them
- View source details and available agents

**Relationship to agent deployment:**
- `agent-source` commands: Manage repository configuration
- `agents` commands: Deploy and interact with agents

**Configuration file:** `~/.claude-mpm/agent-sources.yaml`

---

## Subcommands

### `add` - Add Agent Source

Add a new Git repository as an agent source.

**Syntax:**
```bash
claude-mpm agent-source add <git-url> [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `git-url` | string | Yes | Full Git repository URL (HTTPS) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--subdirectory` | string | None | Subdirectory containing agents |
| `--priority` | integer | 100 | Priority for conflict resolution (0-1000, lower = higher precedence) |
| `--disabled` | flag | False | Add source but keep it disabled |

**Examples:**

```bash
# Add official repository
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# Add with subdirectory
claude-mpm agent-source add https://github.com/myorg/devtools \
  --subdirectory agents

# Add with high priority (low number = high precedence)
claude-mpm agent-source add https://github.com/myteam/agents \
  --priority 10

# Add multiple options
claude-mpm agent-source add https://github.com/experimental/agents \
  --subdirectory tools/agents \
  --priority 200 \
  --disabled
```

**URL Requirements:**
- Must use `http://` or `https://` protocol
- Must be a GitHub URL (github.com domain)
- SSH URLs not supported (`git@github.com:...`)
- Local paths not supported (use `file://` for local repos)

**Valid URL Formats:**
```bash
# ✓ Valid
https://github.com/owner/repo
https://github.com/owner/repo.git
http://github.com/owner/repo

# ✗ Invalid
git@github.com:owner/repo.git  # SSH not supported
github.com/owner/repo          # Missing protocol
/local/path/to/repo            # Local paths not supported
```

**Source ID Generation:**

When you add a source, an identifier is automatically generated:
- `https://github.com/owner/repo` → `owner/repo`
- With `--subdirectory agents` → `owner/repo/agents`

This ID is used in other commands (list, show, remove, etc.).

**Exit Codes:**
- `0` - Success (source added)
- `1` - Error (invalid URL, duplicate source, configuration error)

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| Source already configured | Duplicate URL/ID | Remove existing source first or use different subdirectory |
| Invalid Git URL format | Wrong URL format | Use HTTPS format: `https://github.com/owner/repo` |
| Failed to create config | Permission error | Check write permissions for `~/.claude-mpm/` |

**Related Commands:**
- `agent-source list` - View added sources
- `agent-source update` - Sync agents from source
- `agent-source show` - View source details

---

### `list` - List Agent Sources

List all configured agent sources.

**Syntax:**
```bash
claude-mpm agent-source list [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--by-priority` | flag | False | Sort by priority (lowest first) |
| `--enabled-only` | flag | False | Show only enabled sources |
| `--json` | flag | False | Output as JSON |

**Examples:**

```bash
# List all sources
claude-mpm agent-source list

# Sort by priority (lowest priority number first)
claude-mpm agent-source list --by-priority

# Show only enabled sources
claude-mpm agent-source list --enabled-only

# JSON output for scripting
claude-mpm agent-source list --json

# Combine options
claude-mpm agent-source list --enabled-only --by-priority
```

**Default Output Format:**

```
Agent Sources (3):

✓ myteam/agents
  URL: https://github.com/myteam/agents
  Priority: 10
  Status: Enabled
  Last Synced: 2025-11-30 14:30:00

✓ bobmatnyc/claude-mpm-agents
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Priority: 100
  Status: Enabled
  Last Synced: 2025-11-30 14:25:00

✗ experimental/agents
  URL: https://github.com/experimental/agents
  Priority: 200
  Status: Disabled
  Last Synced: Never
```

**Output Symbols:**
- `✓` - Source enabled
- `✗` - Source disabled

**JSON Output Format:**

```json
{
  "sources": [
    {
      "id": "myteam/agents",
      "url": "https://github.com/myteam/agents",
      "subdirectory": null,
      "priority": 10,
      "enabled": true,
      "last_synced": "2025-11-30T14:30:00",
      "etag": "W/\"abc123\""
    },
    {
      "id": "bobmatnyc/claude-mpm-agents",
      "url": "https://github.com/bobmatnyc/claude-mpm-agents",
      "subdirectory": null,
      "priority": 100,
      "enabled": true,
      "last_synced": "2025-11-30T14:25:00",
      "etag": "W/\"def456\""
    },
    {
      "id": "experimental/agents",
      "url": "https://github.com/experimental/agents",
      "subdirectory": "agents",
      "priority": 200,
      "enabled": false,
      "last_synced": null,
      "etag": null
    }
  ],
  "count": 3,
  "enabled_count": 2
}
```

**Exit Codes:**
- `0` - Success (sources listed)
- `1` - Error (configuration error, no sources configured)

**Use Cases:**
- **Quick overview**: `list` - See all sources at a glance
- **Priority audit**: `list --by-priority` - Check resolution order
- **Production check**: `list --enabled-only` - See active sources
- **Scripting**: `list --json` - Parse in scripts

**Related Commands:**
- `agent-source show <id>` - Detailed view of specific source
- `agent-source update` - Sync sources
- `doctor --checks agent-sources` - Health check

---

### `update` - Sync Agent Sources

Update (sync) agents from Git repositories to local cache.

**Syntax:**
```bash
claude-mpm agent-source update [source-id] [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-id` | string | No | Specific source to update (omit for all enabled sources) |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | flag | False | Force update even if cache is fresh |

**Examples:**

```bash
# Update all enabled sources
claude-mpm agent-source update

# Update specific source
claude-mpm agent-source update bobmatnyc/claude-mpm-agents

# Force update (bypass cache TTL)
claude-mpm agent-source update --force

# Force update specific source
claude-mpm agent-source update myteam/agents --force
```

**Update Process:**

1. **Fetch**: Download latest content from Git repository
2. **Extract**: Find agent markdown files in configured subdirectory
3. **Validate**: Check agent file format
4. **Cache**: Store agents in local cache directory
5. **Record**: Update last-synced timestamp and ETag

**Cache Behavior:**
- **Default TTL**: 24 hours
- **Fresh cache**: Skipped unless `--force` used
- **Stale cache**: Automatically updated
- **Cache location**: `~/.claude-mpm/agent-sources/<source-id>/`

**Output:**

```
Updating agent sources...

✓ myteam/agents - Updated (3 agents)
✓ bobmatnyc/claude-mpm-agents - Cached (5 agents)
✗ experimental/agents - Skipped (disabled)

Updated 1/3 sources, 1 from cache (8 agents total)
```

**Status Indicators:**
- `Updated` - Fetched from remote repository
- `Cached` - Used existing cache (fresh)
- `Skipped` - Source disabled
- `Error` - Update failed (network, validation, etc.)

**Exit Codes:**
- `0` - Success (all sources updated or cached)
- `1` - Partial failure (some sources failed)
- `2` - Complete failure (all sources failed)

**Common Issues:**

| Issue | Cause | Solution |
|-------|-------|----------|
| Network timeout | Slow connection, large repo | Retry with `--force`, check network |
| Authentication failed | Private repo, invalid token | Use token in URL for private repos |
| No agents found | Wrong subdirectory | Check `--subdirectory` configuration |
| Cache permission error | Read-only filesystem | Check permissions on `~/.claude-mpm/` |

**When to Update:**
- After adding new source
- When repository maintainers announce changes
- Before deploying new agents
- Regularly (weekly recommended for active sources)

**Related Commands:**
- `agent-source add` - Add source before updating
- `agent-source list` - See last update times
- `agents available` - View available agents after update
- `doctor --checks agent-sources` - Verify update success

---

### `enable` - Enable Agent Source

Enable a previously disabled source.

**Syntax:**
```bash
claude-mpm agent-source enable <source-id>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-id` | string | Yes | Source identifier to enable |

**Examples:**

```bash
# Enable a source
claude-mpm agent-source enable experimental/agents

# Verify enabled
claude-mpm agent-source list --enabled-only

# Enable and immediately update
claude-mpm agent-source enable myteam/agents && \
  claude-mpm agent-source update myteam/agents
```

**Effect:**
- Source marked as enabled in configuration
- Next `update` command will sync this source
- Agents become available for deployment via `agents available`
- Cached agents immediately available (no update required)

**Exit Codes:**
- `0` - Success (source enabled)
- `1` - Error (source not found, already enabled)

**Use Cases:**
- Re-enable temporarily disabled source
- Activate source added with `--disabled`
- Seasonal agent activation (project-specific)
- Testing workflow (disable → test → enable)

**Related Commands:**
- `agent-source disable` - Disable source
- `agent-source list` - Check enabled status
- `agent-source update` - Sync enabled sources

---

### `disable` - Disable Agent Source

Disable a source without removing it from configuration.

**Syntax:**
```bash
claude-mpm agent-source disable <source-id>
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-id` | string | Yes | Source identifier to disable |

**Examples:**

```bash
# Disable a source
claude-mpm agent-source disable experimental/agents

# Verify disabled
claude-mpm agent-source list

# Check only enabled sources
claude-mpm agent-source list --enabled-only
```

**Effect:**
- Source marked as disabled in configuration
- Skipped during `update` command
- Agents unavailable for deployment
- Cached agents remain (for quick re-enable)
- Configuration preserved (can re-enable anytime)

**What's NOT affected:**
- Already deployed agents remain active
- Cache directory remains intact
- Source configuration stays in file

**Exit Codes:**
- `0` - Success (source disabled)
- `1` - Error (source not found, already disabled)

**Use Cases:**
- Temporarily remove agents from discovery
- Test configuration without deletion
- Manage seasonal/project-specific agents
- Resolve priority conflicts temporarily
- Production vs development environments

**Related Commands:**
- `agent-source enable` - Re-enable source
- `agent-source remove` - Permanently remove
- `agent-source list` - Check status

---

### `show` - Show Source Details

Show detailed information about a specific agent source.

**Syntax:**
```bash
claude-mpm agent-source show <source-id> [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-id` | string | Yes | Source identifier |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--agents` | flag | False | Include list of agents from this source |

**Examples:**

```bash
# Basic details
claude-mpm agent-source show bobmatnyc/claude-mpm-agents

# Include agent list
claude-mpm agent-source show bobmatnyc/claude-mpm-agents --agents

# Show and pipe to less
claude-mpm agent-source show myteam/agents --agents | less
```

**Output (without `--agents`):**

```
Source: bobmatnyc/claude-mpm-agents
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Subdirectory: None
  Priority: 100
  Enabled: Yes
  Last Synced: 2025-11-30 14:30:00
  ETag: W/"abc123"
  Cache Path: ~/.claude-mpm/agent-sources/bobmatnyc/claude-mpm-agents
  Agents Count: 5
```

**Output (with `--agents`):**

```
Source: bobmatnyc/claude-mpm-agents
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Subdirectory: None
  Priority: 100
  Enabled: Yes
  Last Synced: 2025-11-30 14:30:00
  ETag: W/"abc123"
  Cache Path: ~/.claude-mpm/agent-sources/bobmatnyc/claude-mpm-agents
  Agents Count: 5

  Agents (5):
    ✓ agent-manager - Manage and improve agent definitions
      File: agent-manager.md
      Size: 12.3 KB

    ✓ rust-engineer - Specialized Rust development agent
      File: rust-engineer.md
      Size: 8.5 KB

    ✓ espocrm-developer - EspoCRM development expert
      File: espocrm-developer.md
      Size: 15.2 KB

    ✓ data-analyst - Data analysis and visualization
      File: data-analyst.md
      Size: 10.1 KB

    ✓ devops-engineer - DevOps and infrastructure automation
      File: devops-engineer.md
      Size: 11.7 KB
```

**Field Descriptions:**

| Field | Description |
|-------|-------------|
| URL | Git repository URL |
| Subdirectory | Path within repo (None if root) |
| Priority | Conflict resolution priority (lower = higher precedence) |
| Enabled | Whether source is active |
| Last Synced | Timestamp of last successful sync (Never if not synced) |
| ETag | HTTP ETag for cache validation |
| Cache Path | Local cache directory |
| Agents Count | Number of agents in this source |

**Exit Codes:**
- `0` - Success (source details shown)
- `1` - Error (source not found, cache error)

**Use Cases:**
- Verify source configuration
- Check last sync time
- Browse available agents
- Troubleshoot cache issues
- Audit source priority

**Related Commands:**
- `agent-source list` - Overview of all sources
- `agent-source update` - Sync agents
- `agents available` - List all available agents

---

### `remove` - Remove Agent Source

Remove an agent source from configuration.

**Syntax:**
```bash
claude-mpm agent-source remove <source-id> [OPTIONS]
```

**Arguments:**

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `source-id` | string | Yes | Source identifier to remove |

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--force` | flag | False | Skip confirmation prompt |

**Examples:**

```bash
# Remove with confirmation
claude-mpm agent-source remove experimental/agents

# Remove without confirmation (careful!)
claude-mpm agent-source remove experimental/agents --force

# Remove and verify
claude-mpm agent-source remove old-source --force && \
  claude-mpm agent-source list
```

**Confirmation Prompt:**

```
Remove agent source 'experimental/agents'?
  URL: https://github.com/experimental/agents
  Priority: 200
  Subdirectory: agents
  Agents: 3

This will remove the source configuration but keep cached agents.
Already-deployed agents will remain active.

Continue? [y/N]:
```

**Effect:**
- Source removed from `agent-sources.yaml`
- Source no longer appears in `list`
- Source cannot be updated anymore

**What's Preserved:**
- Cached agents in `~/.claude-mpm/agent-sources/<source-id>/`
- Already-deployed agents remain active
- Can re-add source later with same or different configuration

**What's NOT Done:**
- Does NOT delete cache directory
- Does NOT undeploy agents from this source
- Does NOT affect other sources

**To Completely Remove:**

```bash
# 1. Remove source configuration
claude-mpm agent-source remove myteam/agents --force

# 2. Undeploy agents from this source (manual)
claude-mpm agents undeploy agent-name-1
claude-mpm agents undeploy agent-name-2

# 3. Delete cache directory (optional)
rm -rf ~/.claude-mpm/agent-sources/myteam/agents/
```

**Exit Codes:**
- `0` - Success (source removed)
- `1` - Error (source not found, user cancelled)

**Use Cases:**
- Clean up unused sources
- Replace source with updated configuration
- Remove deprecated repositories
- Troubleshoot configuration issues

**Related Commands:**
- `agent-source disable` - Temporary alternative (keeps configuration)
- `agents undeploy` - Remove deployed agents
- `agent-source list` - Verify removal

---

## Common Options

### Global Options

These options work with all `agent-source` subcommands:

| Option | Description |
|--------|-------------|
| `--config <path>` | Use alternative configuration directory |
| `--verbose`, `-v` | Show detailed output |
| `--quiet`, `-q` | Suppress non-error output |
| `--help`, `-h` | Show help message |

**Examples:**

```bash
# Use custom config directory
claude-mpm --config ~/.claude-mpm-dev agent-source list

# Verbose output for debugging
claude-mpm agent-source update --verbose

# Quiet mode for scripting
claude-mpm agent-source update --quiet

# Show help
claude-mpm agent-source --help
claude-mpm agent-source add --help
```

---

## Exit Codes

Standard exit codes for all `agent-source` commands:

| Code | Meaning | Description |
|------|---------|-------------|
| `0` | Success | Command completed successfully |
| `1` | Error | Command failed (validation, network, etc.) |
| `2` | Partial Failure | Some operations failed (multi-source update) |

**Usage in scripts:**

```bash
#!/bin/bash

# Exit on error
set -e

# Add source (exits 1 on failure)
claude-mpm agent-source add https://github.com/org/agents

# Update sources (check exit code)
if claude-mpm agent-source update --force; then
    echo "Update successful"
else
    echo "Update failed with code $?"
    exit 1
fi

# List sources (parse JSON)
sources=$(claude-mpm agent-source list --json)
echo "Sources: $sources"
```

---

## Examples

### Complete Workflow

```bash
# 1. Add official repository
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# 2. Add organization repository with high priority
claude-mpm agent-source add https://github.com/myorg/agents \
  --priority 10 \
  --subdirectory tools/agents

# 3. List sources to verify
claude-mpm agent-source list --by-priority

# 4. Update all sources
claude-mpm agent-source update

# 5. Show details of specific source
claude-mpm agent-source show myorg/agents --agents

# 6. Verify with doctor
claude-mpm doctor --checks agent-sources

# 7. List available agents
claude-mpm agents available

# 8. Deploy agent from source
claude-mpm agents deploy agent-manager
```

---

### Priority Management

```bash
# Add sources with distinct priorities
claude-mpm agent-source add https://github.com/team/agents --priority 10
claude-mpm agent-source add https://github.com/community/agents --priority 50
claude-mpm agent-source add https://github.com/experimental/agents \
  --priority 200 --disabled

# View by priority
claude-mpm agent-source list --by-priority

# Output:
# ✓ team/agents (priority: 10)
# ✓ community/agents (priority: 50)
# ✗ experimental/agents (priority: 200, disabled)
```

---

### Testing and Development

```bash
# Add experimental source (disabled)
claude-mpm agent-source add https://github.com/dev/beta-agents \
  --priority 5 \
  --disabled

# Enable and test
claude-mpm agent-source enable dev/beta-agents
claude-mpm agent-source update dev/beta-agents
claude-mpm agent-source show dev/beta-agents --agents

# Deploy and test agent
claude-mpm agents deploy test-agent --force

# If issues, disable quickly
claude-mpm agent-source disable dev/beta-agents
```

---

### Scripting

```bash
#!/bin/bash
# Update agent sources and report status

set -euo pipefail

# Update sources
echo "Updating agent sources..."
if claude-mpm agent-source update --force; then
    echo "✓ Update successful"
else
    echo "✗ Update failed"
    exit 1
fi

# Get source count
sources=$(claude-mpm agent-source list --json | jq '.count')
echo "Total sources: $sources"

# Get enabled count
enabled=$(claude-mpm agent-source list --enabled-only --json | jq '.count')
echo "Enabled sources: $enabled"

# Check health
echo "Running diagnostics..."
if claude-mpm doctor --checks agent-sources --quiet; then
    echo "✓ All sources healthy"
else
    echo "⚠ Health check warnings detected"
    claude-mpm doctor --checks agent-sources --verbose
fi
```

---

### Multiple Environments

```bash
# Development environment
export CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-dev
claude-mpm agent-source add https://github.com/dev/agents --priority 1
claude-mpm agent-source update

# Production environment
export CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-prod
claude-mpm agent-source add https://github.com/stable/agents --priority 50
claude-mpm agent-source update

# Switch between environments
alias mpm-dev='CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-dev claude-mpm'
alias mpm-prod='CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-prod claude-mpm'

mpm-dev agent-source list
mpm-prod agent-source list
```

---

## Related Commands

### Agent Management
- `claude-mpm agents available` - List all available agents (from all sources)
- `claude-mpm agents deploy <name>` - Deploy agent from source
- `claude-mpm agents undeploy <name>` - Remove deployed agent
- `claude-mpm agents list-deployed` - Show deployed agents

### Diagnostics
- `claude-mpm doctor` - Full system health check
- `claude-mpm doctor --checks agent-sources` - Agent sources health check
- `claude-mpm doctor --verbose` - Detailed diagnostics

### Configuration
- `claude-mpm configure` - Interactive configuration
- `claude-mpm config show` - Show current configuration

### Related Features
- **Skills**: `claude-mpm skill-source` - Similar system for skills
- **Agents**: `claude-mpm agents` - Agent deployment and management

---

## See Also

### User Documentation
- **[Agent Sources User Guide](../user/agent-sources.md)** - Complete user guide with examples
- **[User Guide](../user/user-guide.md)** - General Claude MPM usage
- **[Troubleshooting](../user/troubleshooting.md)** - Common issues and solutions

### Reference Documentation
- **[Agent Sources API](agent-sources-api.md)** - Technical API reference
- **[Configuration](configuration.md)** - Configuration file reference
- **[CLI Doctor](cli-doctor.md)** - Doctor command reference

### Related Topics
- **[Skills System](../user/skills-guide.md)** - Similar system for reusable knowledge
- **[Agent Deployment](../developer/README.md)** - Agent deployment architecture

---

**Version:** 4.26.5 (2025-11-30)
**Related Ticket:** [1M-442 - Agent git sources configured but not syncing or loading](https://linear.app/workspace/issue/1M-442)
