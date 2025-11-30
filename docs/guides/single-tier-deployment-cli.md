# Single-Tier Deployment CLI Guide

**Phase 2 Implementation - Agent Source Management**

## Overview

The single-tier deployment system manages agents from Git repositories with priority-based conflict resolution. This guide covers the new `source` and `agents` commands introduced in Phase 2.

## Quick Start

### 1. Add a Custom Agent Repository

```bash
# Add repository with default priority (100)
claude-mpm source add https://github.com/your-org/custom-agents

# Add with subdirectory and custom priority
claude-mpm source add https://github.com/your-org/agents \
  --subdirectory backend/agents \
  --priority 50
```

**Priority System**: Lower number = higher precedence
- Priority 0-49: Highest precedence (overrides system agents)
- Priority 50-99: High precedence
- Priority 100: Default (same as system repository)
- Priority 101+: Lower precedence

### 2. List Configured Sources

```bash
# List enabled repositories
claude-mpm source list

# List all repositories (including disabled)
claude-mpm source list --all
```

**Output Example**:
```
Configured Agent Sources:
  [✓] owner/repo/agents (priority: 50)
      URL: https://github.com/owner/repo
      Subdirectory: agents
  [✓] bobmatnyc/claude-mpm-agents/agents (priority: 100) [SYSTEM]
      URL: https://github.com/bobmatnyc/claude-mpm-agents
      Subdirectory: agents
```

### 3. Sync Repositories

```bash
# Sync all repositories (uses ETag caching)
claude-mpm source sync

# Force sync (ignore cache)
claude-mpm source sync --force

# Sync specific repository
claude-mpm source sync owner/repo/agents
```

### 4. Deploy Agents

```bash
# Preview deployment (dry run)
claude-mpm agents deploy-all --dry-run

# Deploy all agents from sources
claude-mpm agents deploy-all

# Force sync before deployment
claude-mpm agents deploy-all --force-sync

# List available agents
claude-mpm agents available

# List from specific source
claude-mpm agents available --source owner/repo/agents
```

## Command Reference

### Source Commands

#### `source add`
Add a new agent source repository.

```bash
claude-mpm source add <URL> [OPTIONS]

Arguments:
  URL                  GitHub repository URL

Options:
  --subdirectory PATH  Subdirectory within repository (e.g., 'agents')
  --priority N         Priority for conflict resolution (default: 100)
  --disabled           Add but keep disabled
```

**Examples**:
```bash
# Basic usage
claude-mpm source add https://github.com/owner/repo

# With subdirectory and high priority
claude-mpm source add https://github.com/owner/repo \
  --subdirectory backend/agents \
  --priority 25

# Add disabled (for later activation)
claude-mpm source add https://github.com/owner/repo --disabled
```

#### `source remove`
Remove an agent source repository.

```bash
claude-mpm source remove <IDENTIFIER>

Arguments:
  IDENTIFIER  Repository identifier (e.g., 'owner/repo' or 'owner/repo/agents')
```

**Examples**:
```bash
# Remove repository
claude-mpm source remove owner/repo

# Remove with subdirectory
claude-mpm source remove owner/repo/agents
```

#### `source list`
List configured agent source repositories.

```bash
claude-mpm source list [OPTIONS]

Options:
  --all  Show disabled repositories (default: only enabled)
```

**Output Format**:
```
Configured Agent Sources:
  [✓] high-priority/repo (priority: 50)
      URL: https://github.com/high-priority/repo
      Last synced: 2025-11-30 10:00:00 UTC

  [✗] disabled/repo (priority: 100) [DISABLED]
      URL: https://github.com/disabled/repo

  [✓] bobmatnyc/claude-mpm-agents/agents (priority: 100) [SYSTEM]
      URL: https://github.com/bobmatnyc/claude-mpm-agents
```

#### `source enable`
Enable a disabled repository.

```bash
claude-mpm source enable <IDENTIFIER>
```

#### `source disable`
Disable a repository.

```bash
claude-mpm source disable <IDENTIFIER>
```

#### `source disable-system`
Disable or enable the default system repository.

```bash
claude-mpm source disable-system [OPTIONS]

Options:
  --enable  Re-enable system repository instead of disabling
```

**Examples**:
```bash
# Disable system repository
claude-mpm source disable-system

# Re-enable system repository
claude-mpm source disable-system --enable
```

#### `source sync`
Sync agent sources from Git.

```bash
claude-mpm source sync [OPTIONS] [IDENTIFIER]

Arguments:
  IDENTIFIER  Optional: Sync only this repository (default: sync all)

Options:
  --force     Force sync even if cache is fresh (ignore ETags)
```

**Examples**:
```bash
# Sync all repositories
claude-mpm source sync

# Force sync all (ignore cache)
claude-mpm source sync --force

# Sync specific repository
claude-mpm source sync owner/repo/agents
```

### Agent Commands

#### `agents deploy-all`
Deploy all agents from configured sources.

```bash
claude-mpm agents deploy-all [OPTIONS]

Options:
  --force-sync  Force repository sync before deploying (ignore cache)
  --dry-run     Show what would be deployed without actually deploying
```

**Workflow**:
1. Sync all enabled repositories (or use cache)
2. Discover all agents from repositories
3. Resolve conflicts using priority system
4. Deploy agents to `.claude/agents/`
5. Report deployment results

**Output Example**:
```
Syncing repositories...
  ✓ owner/repo/agents (2 files updated)
  ✓ bobmatnyc/claude-mpm-agents/agents (0 files, cached)

Discovering agents...
  Found 5 agents

Resolving conflicts...
  Conflict: 'engineer' found in 2 sources
    → Using owner/repo/agents (priority: 50)

Deploying agents...
  ✓ Engineer (from owner/repo/agents)
  ✓ Research (from bobmatnyc/claude-mpm-agents/agents)
  ✓ QA (from owner/repo/agents)

Summary:
  Repositories synced: 2
  Agents discovered: 5
  Agents deployed: 3
  Conflicts resolved: 1
```

**Dry Run Example**:
```bash
claude-mpm agents deploy-all --dry-run

# Output:
Would deploy:
  [DRY RUN] Engineer (from owner/repo/agents, priority: 50)
  [DRY RUN] Research (from bobmatnyc/claude-mpm-agents/agents, priority: 100)
```

#### `agents available`
List available agents from all configured sources.

```bash
claude-mpm agents available [OPTIONS]

Options:
  --source TEXT       Filter by source repository (e.g., 'owner/repo/agents')
  --format [table|json|simple]  Output format (default: table)
```

**Output Formats**:

**Table** (default):
```
Available Agents:
┌──────────┬─────────────────────┬──────────┬─────────────────────┐
│ Name     │ Source              │ Priority │ Version             │
├──────────┼─────────────────────┼──────────┼─────────────────────┤
│ Engineer │ owner/repo/agents   │ 50       │ abc123...           │
│ Research │ system/agents       │ 100      │ def456...           │
│ QA       │ owner/repo/agents   │ 50       │ ghi789...           │
└──────────┴─────────────────────┴──────────┴─────────────────────┘
```

**JSON**:
```json
[
  {
    "name": "Engineer",
    "agent_id": "engineer",
    "description": "Python specialist",
    "source": "owner/repo/agents",
    "priority": 50,
    "version": "abc123...",
    "model": "sonnet"
  }
]
```

**Simple**:
```
engineer (from owner/repo/agents)
research (from system/agents)
qa (from owner/repo/agents)
```

## Workflows

### Adding a Custom Team Repository

```bash
# 1. Add your team's agent repository
claude-mpm source add https://github.com/yourteam/agents \
  --subdirectory backend \
  --priority 25

# 2. Verify configuration
claude-mpm source list

# 3. Preview deployment
claude-mpm agents deploy-all --dry-run

# 4. Deploy agents
claude-mpm agents deploy-all

# 5. Verify deployed agents
claude-mpm agents available
```

### Managing Priority Conflicts

When multiple repositories provide the same agent:

```bash
# 1. List all available agents to see sources
claude-mpm agents available

# Output shows conflicts:
# Engineer (from owner/repo, priority: 50)
# Engineer (from system, priority: 100)

# 2. Lower priority wins (50 < 100)
# Deploy will use owner/repo version

# 3. To prefer system version, increase custom repo priority:
claude-mpm source remove owner/repo
claude-mpm source add https://github.com/owner/repo \
  --priority 150  # Lower precedence than system (100)
```

### Disabling System Agents

To use only custom agents:

```bash
# 1. Disable system repository
claude-mpm source disable-system

# 2. Add your custom repository
claude-mpm source add https://github.com/yourteam/agents

# 3. Deploy
claude-mpm agents deploy-all

# 4. To re-enable system agents later:
claude-mpm source disable-system --enable
```

### Force Updating Cached Agents

```bash
# 1. Force sync to get latest agent versions
claude-mpm source sync --force

# 2. Redeploy all agents
claude-mpm agents deploy-all

# Or combine both:
claude-mpm agents deploy-all --force-sync
```

## Configuration File

Agent sources are stored in: `~/.claude-mpm/config/agent_sources.yaml`

**Example Configuration**:
```yaml
disable_system_repo: false
repositories:
  - url: https://github.com/yourteam/agents
    subdirectory: backend
    enabled: true
    priority: 50
  - url: https://github.com/anotherteam/agents
    enabled: false
    priority: 100
```

**Manual Editing**:
While you can edit this file manually, using CLI commands is recommended for validation and consistency.

## Cache Management

Agent sources are cached in: `~/.claude-mpm/cache/remote-agents/`

**Cache Structure**:
```
~/.claude-mpm/cache/remote-agents/
├── owner/
│   └── repo/
│       ├── agents/
│       │   ├── engineer.md
│       │   └── research.md
│       └── .meta.json
```

**Cache Benefits**:
- ETag-based incremental updates
- Reduces network requests
- Works offline with cached agents
- Automatic SHA-256 version tracking

**Manual Cache Clearing**:
```bash
# Remove cache directory
rm -rf ~/.claude-mpm/cache/remote-agents/

# Next sync will rebuild cache
claude-mpm source sync
```

## Troubleshooting

### "Repository not found" Error

```bash
# Check configured repositories
claude-mpm source list --all

# Verify repository identifier format
# Should be: owner/repo or owner/repo/subdirectory
```

### "Agent not found" Error

```bash
# List available agents
claude-mpm agents available

# Sync repositories
claude-mpm source sync --force

# Verify repository is enabled
claude-mpm source list
```

### Priority Conflicts Not Resolving

```bash
# Check priorities
claude-mpm source list

# Remember: LOWER priority number = HIGHER precedence
# Priority 50 overrides priority 100

# Update priority if needed
claude-mpm source remove owner/repo
claude-mpm source add https://github.com/owner/repo --priority 25
```

### Deployment Fails

```bash
# Check for errors with dry run
claude-mpm agents deploy-all --dry-run

# Force sync to refresh cache
claude-mpm agents deploy-all --force-sync

# Check logs in ~/.claude-mpm/logs/
```

## Best Practices

### 1. Priority Management
- Use 0-49 for team-specific overrides
- Use 50-99 for experimental agents
- Keep system at 100 (default)
- Use 101+ for low-priority testing

### 2. Repository Organization
- Keep agents in dedicated subdirectories
- Use descriptive repository names
- Document agent changes in README
- Version agents using Git tags

### 3. Regular Maintenance
```bash
# Weekly: Sync all repositories
claude-mpm source sync --force

# Monthly: Review and clean up
claude-mpm source list --all
claude-mpm agents available

# Remove unused repositories
claude-mpm source remove old/repo
```

### 4. Team Collaboration
- Share agent_sources.yaml configuration
- Document custom agent repositories
- Coordinate priority assignments
- Test with --dry-run before deploying

## Migration from Multi-Tier

Coming in Phase 3:
- Automatic migration from PROJECT/USER/SYSTEM tiers
- Configuration import tools
- Backward compatibility mode
- Migration verification

## See Also

- [Phase 2 Implementation Summary](../implementation/phase-2-single-tier-deployment-summary.md)
- [Agent Deployment Research](../research/agent-deployment-single-tier-migration-2025-11-30.md)
- Agent Source Configuration API Documentation (coming in Phase 3)
