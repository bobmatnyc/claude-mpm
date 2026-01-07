---
title: Agent Sources User Guide
version: 4.26.5
last_updated: 2025-11-30
status: current
related_ticket: 1M-442
---

# Agent Sources User Guide

Complete guide to using and managing agent source repositories in Claude MPM.

## Table of Contents

- [Overview](#overview)
- [What Are Agent Sources?](#what-are-agent-sources)
- [Quick Start](#quick-start)
- [Managing Agent Sources](#managing-agent-sources)
- [Agent Discovery System](#agent-discovery-system)
- [Priority System](#priority-system)
- [CLI Command Reference](#cli-command-reference)
- [Agent Improvement Workflow](#agent-improvement-workflow)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)
- [Advanced Topics](#advanced-topics)

## Overview

### What Are Agent Sources?

Agent sources are Git repositories containing agent definition files (markdown files) that extend Claude MPM with additional agents beyond the built-in system agents. Think of them as community-contributed or organization-specific agent libraries:

- **Git-Based**: Agents stored in version-controlled repositories
- **Remote Sync**: Automatically fetch and update agents from repositories
- **Priority System**: Control which agents take precedence when names conflict
- **Enable/Disable**: Toggle repositories without removing them
- **Multi-Repository**: Support multiple sources with different priorities

**Key Benefits:**
- **Community Agents**: Use agents shared by the Claude MPM community
- **Organization Libraries**: Create internal agent repositories for your team
- **Version Control**: Track agent changes through Git history
- **Easy Updates**: Sync latest agent improvements with one command
- **Contribution**: Propose improvements back to agent repositories

### When to Use Agent Sources vs Built-in Agents

**Use Agent Sources When:**
- You want community-contributed specialized agents
- You need organization-specific agents shared across teams
- You want to propose improvements to existing agents
- You need agents for specific frameworks or workflows
- You want to experiment with custom agents before contributing

**Use Built-in Agents When:**
- Standard agents (engineer, research, qa, etc.) meet your needs
- You're just getting started with Claude MPM
- You prefer stable, well-tested agents
- You don't need specialized domain expertise

**Example:** The built-in "engineer" agent handles general development, but you might add a source with specialized agents like "rust-engineer" or "espocrm-developer" for specific technologies.

---

## Quick Start

### Adding Your First Agent Source

The official Claude MPM agents repository provides community-contributed agents:

```bash
# 1. Add the official agents repository
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# 2. Sync agents from the repository
claude-mpm agent-source update

# 3. List available agents from all sources
claude-mpm agents available

# 4. Deploy an agent from the source
claude-mpm agents deploy <agent-name>
```

### Verifying Agent Sources

After adding sources, verify they're working correctly:

```bash
# Check agent source health
claude-mpm doctor --checks agent-sources

# List configured sources
claude-mpm agent-source list

# Show details for a specific source
claude-mpm agent-source show <source-id>
```

---

## Managing Agent Sources

### Adding a Source

Add a new Git repository as an agent source:

```bash
# Basic usage (uses default priority: 100)
claude-mpm agent-source add <git-url>

# With custom subdirectory
claude-mpm agent-source add <git-url> --subdirectory agents

# With custom priority (lower number = higher precedence)
claude-mpm agent-source add <git-url> --priority 50

# Add disabled (useful for testing configuration)
claude-mpm agent-source add <git-url> --disabled
```

**Examples:**

```bash
# Official repository
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# Organization repository with subdirectory
claude-mpm agent-source add https://github.com/myorg/devtools --subdirectory agents

# High-priority custom repository (priority 10)
claude-mpm agent-source add https://github.com/myteam/agents --priority 10

# Add repository for later use (disabled)
claude-mpm agent-source add https://github.com/experimental/agents --disabled
```

**Source Identifier Generation:**

When you add a source, Claude MPM generates an identifier based on the URL:
- `https://github.com/owner/repo` → `owner/repo`
- `https://github.com/owner/repo` with `--subdirectory agents` → `owner/repo/agents`

This identifier is used in other commands (list, show, remove, etc.).

### Listing Sources

View all configured agent sources:

```bash
# Basic list (shows all sources)
claude-mpm agent-source list

# Sort by priority (lowest first)
claude-mpm agent-source list --by-priority

# Show only enabled sources
claude-mpm agent-source list --enabled-only

# JSON output (for scripting)
claude-mpm agent-source list --json
```

**Example Output:**

```
Agent Sources:
  ✓ bobmatnyc/claude-mpm-agents
    URL: https://github.com/bobmatnyc/claude-mpm-agents
    Priority: 100
    Status: Enabled
    Last Synced: 2025-11-30 14:30:00

  ✗ experimental/agents
    URL: https://github.com/experimental/agents
    Priority: 200
    Status: Disabled
    Last Synced: Never
```

### Updating (Syncing) Sources

Sync agents from Git repositories to your local cache:

```bash
# Update all enabled sources
claude-mpm agent-source update

# Update specific source only
claude-mpm agent-source update <source-id>

# Force update (ignore cache freshness)
claude-mpm agent-source update --force
```

**What happens during update:**
1. Fetches latest content from Git repository
2. Extracts agent markdown files from configured subdirectory
3. Caches agents locally for fast deployment
4. Updates last-synced timestamp
5. Validates agent file format

**Update frequency:**
- Manual: Run `update` command when you want latest agents
- Automatic: Not implemented yet (planned feature)
- Recommendation: Update weekly or when agent repository announces changes

### Enabling and Disabling Sources

Toggle sources without removing them:

```bash
# Disable a source (agents no longer available)
claude-mpm agent-source disable <source-id>

# Re-enable a source (agents available again)
claude-mpm agent-source enable <source-id>
```

**Use cases:**
- **Testing**: Disable experimental sources in production
- **Conflicts**: Temporarily disable source causing agent name conflicts
- **Maintenance**: Disable sources during repository maintenance
- **Organization**: Keep sources configured but disabled until needed

### Showing Source Details

View detailed information about a source:

```bash
# Basic details
claude-mpm agent-source show <source-id>

# Include list of agents from this source
claude-mpm agent-source show <source-id> --agents
```

**Example Output:**

```
Source: bobmatnyc/claude-mpm-agents
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Subdirectory: None
  Priority: 100
  Enabled: Yes
  Last Synced: 2025-11-30 14:30:00
  Cache Path: ~/.claude-mpm/agent-sources/bobmatnyc/claude-mpm-agents

  Agents (5):
    - agent-manager - Manage and improve agent definitions
    - rust-engineer - Specialized Rust development agent
    - espocrm-developer - EspoCRM development expert
    - data-analyst - Data analysis and visualization
    - devops-engineer - DevOps and infrastructure automation
```

### Removing Sources

Remove agent sources you no longer need:

```bash
# Remove with confirmation prompt
claude-mpm agent-source remove <source-id>

# Remove without confirmation (use carefully!)
claude-mpm agent-source remove <source-id> --force
```

**What happens:**
- Source configuration removed from `agent-sources.yaml`
- Cached agents from this source remain (for rollback)
- Deployed agents from this source remain active
- Source can be re-added later

**Important:** Removing a source does NOT automatically remove agents deployed from that source. To remove deployed agents, use `claude-mpm agents undeploy <agent-name>`.

---

## Agent Discovery System

### How Agent Discovery Works

Claude MPM uses a **single-tier priority-based system** to discover and deploy agents. When you run `claude-mpm agents deploy <agent-name>`, the system searches for agents in this order:

**Discovery Order (by priority):**
1. **Local Project Agents** (`.claude-mpm/agents/`)
   - Priority: Always checked first (implicit priority 0)
   - Use case: Project-specific agent overrides

2. **Git Sources by Priority** (lowest priority number first)
   - Priority: Configurable per source (default: 100)
   - Use case: Organization or community agents

3. **Built-in System Agents** (Package bundled agents)
   - Priority: Always checked last (implicit priority 1000)
   - Use case: Standard Claude MPM agents

**Priority Resolution:**
- Lower number = Higher precedence (priority 10 beats priority 100)
- Same priority = First match wins (order from configuration file)
- Local project agents always override everything
- System agents always provide fallback

### Agent Override Behavior

When multiple sources provide agents with the same name:

```yaml
# Configuration example
repositories:
  - url: https://github.com/myteam/agents
    priority: 10          # Highest precedence (checked first)

  - url: https://github.com/community/agents
    priority: 50          # Medium precedence

  - url: https://github.com/bobmatnyc/claude-mpm-agents
    priority: 100         # Lower precedence (default)
```

**Example scenario:**
- `myteam/agents` has `engineer.md` (specialized for team)
- `community/agents` has `engineer.md` (community version)
- System has `engineer.md` (built-in)

**Result:** When you run `claude-mpm agents deploy engineer`, the team version (priority 10) is used.

**Best practices:**
- Use low priorities (10-50) for trusted organization sources
- Use default priority (100) for community sources
- Use high priorities (200+) for experimental sources
- Check deployment with `claude-mpm doctor --checks agent-sources`

---

## Priority System

### Understanding Priorities

The priority system controls agent resolution when multiple sources provide agents with the same name.

**Priority Ranges:**

| Priority Range | Recommended Use | Example |
|---------------|-----------------|---------|
| 1-50 | Organization/team sources | Internal company agents |
| 51-100 | Trusted community sources | Official repositories |
| 101-200 | Experimental/testing | Beta agents, forks |
| 201-1000 | Low-priority fallbacks | Deprecated sources |

**Default priority:** 100 (assigned when adding source without `--priority`)

### Setting Priorities

```bash
# Add source with high precedence (checked early)
claude-mpm agent-source add <url> --priority 10

# Add source with low precedence (checked late)
claude-mpm agent-source add <url> --priority 200
```

**Changing priority later:**

Currently, to change priority you must:
1. Remove the source: `claude-mpm agent-source remove <source-id>`
2. Re-add with new priority: `claude-mpm agent-source add <url> --priority <new-priority>`

**Note:** Priority changes don't affect already-deployed agents. Redeploy to use new priority.

### Priority Conflict Detection

Use the `doctor` command to detect priority conflicts:

```bash
# Check for conflicts
claude-mpm doctor --checks agent-sources --verbose
```

**Doctor checks for:**
- Multiple sources with same priority
- Agent name conflicts across sources
- Ambiguous resolution scenarios

**Example warning:**

```
⚠ Warning: Priority conflict detected
  Sources 'team/agents' and 'community/agents' both have priority 50
  Agent 'engineer' exists in both sources
  Recommendation: Set different priorities for clarity
```

---

## CLI Command Reference

Complete reference for all `agent-source` commands.

### `add` - Add Agent Source

Add a new Git repository as an agent source.

**Syntax:**
```bash
claude-mpm agent-source add <git-url> [OPTIONS]
```

**Arguments:**
- `git-url` - Full Git repository URL (required)
  - Format: `https://github.com/owner/repo`
  - Must use `http://` or `https://` protocol
  - Must be a GitHub URL

**Options:**
- `--subdirectory <path>` - Subdirectory containing agents (optional)
  - Example: `agents`, `tools/agents`, `backend/agents`
  - Relative path without leading slash

- `--priority <number>` - Priority for conflict resolution (optional)
  - Default: `100`
  - Range: `0-1000`
  - Lower = Higher precedence

- `--disabled` - Add source but keep it disabled (optional)
  - Source won't sync or provide agents until enabled
  - Useful for configuration testing

**Examples:**

```bash
# Basic usage
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# With subdirectory
claude-mpm agent-source add https://github.com/myorg/devtools \
  --subdirectory agents

# High priority with subdirectory
claude-mpm agent-source add https://github.com/myteam/agents \
  --subdirectory tools/agents \
  --priority 10

# Add disabled for testing
claude-mpm agent-source add https://github.com/experimental/agents \
  --disabled
```

**Exit codes:**
- `0` - Success
- `1` - Error (invalid URL, duplicate source, etc.)

---

### `list` - List Agent Sources

List all configured agent sources.

**Syntax:**
```bash
claude-mpm agent-source list [OPTIONS]
```

**Options:**
- `--by-priority` - Sort by priority (lowest first)
- `--enabled-only` - Show only enabled sources
- `--json` - Output as JSON

**Examples:**

```bash
# List all sources
claude-mpm agent-source list

# Sort by priority
claude-mpm agent-source list --by-priority

# Show only enabled
claude-mpm agent-source list --enabled-only

# JSON output for scripting
claude-mpm agent-source list --json
```

**Sample output (default):**

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

**JSON output structure:**

```json
{
  "sources": [
    {
      "id": "myteam/agents",
      "url": "https://github.com/myteam/agents",
      "subdirectory": null,
      "priority": 10,
      "enabled": true,
      "last_synced": "2025-11-30T14:30:00"
    }
  ]
}
```

---

### `update` - Sync Agent Sources

Update (sync) agents from Git repositories.

**Syntax:**
```bash
claude-mpm agent-source update [source-id] [OPTIONS]
```

**Arguments:**
- `source-id` - Specific source to update (optional)
  - If omitted: Updates all enabled sources
  - Format: `owner/repo` or `owner/repo/subdirectory`

**Options:**
- `--force` - Force update even if cache is fresh
  - Bypasses cache TTL checks
  - Useful for testing or after repository changes

**Examples:**

```bash
# Update all enabled sources
claude-mpm agent-source update

# Update specific source
claude-mpm agent-source update bobmatnyc/claude-mpm-agents

# Force update (ignore cache)
claude-mpm agent-source update --force

# Force update specific source
claude-mpm agent-source update myteam/agents --force
```

**What happens during update:**
1. Fetches latest content from Git repository
2. Extracts agent markdown files
3. Validates agent format
4. Updates local cache
5. Records sync timestamp

**Output:**

```
Updating agent sources...

✓ myteam/agents - Updated (3 agents)
✓ bobmatnyc/claude-mpm-agents - Updated (5 agents)
✗ experimental/agents - Skipped (disabled)

Updated 2/3 sources (8 agents total)
```

**Cache behavior:**
- Default TTL: 24 hours
- `--force` bypasses TTL
- Cache stored in: `~/.claude-mpm/agent-sources/`

---

### `enable` - Enable Agent Source

Enable a previously disabled source.

**Syntax:**
```bash
claude-mpm agent-source enable <source-id>
```

**Arguments:**
- `source-id` - Source identifier (required)
  - Format: `owner/repo` or `owner/repo/subdirectory`

**Examples:**

```bash
# Enable a source
claude-mpm agent-source enable experimental/agents

# Verify enabled
claude-mpm agent-source show experimental/agents
```

**Effect:**
- Source becomes available for sync and deployment
- Next `update` command will sync this source
- Agents from this source appear in `agents available`

---

### `disable` - Disable Agent Source

Disable a source without removing it.

**Syntax:**
```bash
claude-mpm agent-source disable <source-id>
```

**Arguments:**
- `source-id` - Source identifier (required)
  - Format: `owner/repo` or `owner/repo/subdirectory`

**Examples:**

```bash
# Disable a source
claude-mpm agent-source disable experimental/agents

# Verify disabled
claude-mpm agent-source list --enabled-only
```

**Effect:**
- Source skipped during `update` command
- Agents from this source unavailable for deployment
- Cached agents remain (for quick re-enable)
- Configuration preserved (can re-enable later)

**Use cases:**
- Temporarily remove agents from discovery
- Test configuration without deleting
- Manage seasonal or project-specific agents

---

### `show` - Show Source Details

Show detailed information about an agent source.

**Syntax:**
```bash
claude-mpm agent-source show <source-id> [OPTIONS]
```

**Arguments:**
- `source-id` - Source identifier (required)
  - Format: `owner/repo` or `owner/repo/subdirectory`

**Options:**
- `--agents` - Include list of agents from this source

**Examples:**

```bash
# Basic details
claude-mpm agent-source show bobmatnyc/claude-mpm-agents

# Include agent list
claude-mpm agent-source show bobmatnyc/claude-mpm-agents --agents
```

**Sample output (without `--agents`):**

```
Source: bobmatnyc/claude-mpm-agents
  URL: https://github.com/bobmatnyc/claude-mpm-agents
  Subdirectory: None
  Priority: 100
  Enabled: Yes
  Last Synced: 2025-11-30 14:30:00
  Cache Path: ~/.claude-mpm/agent-sources/bobmatnyc/claude-mpm-agents
  Agents Count: 5
```

**Sample output (with `--agents`):**

```
Source: bobmatnyc/claude-mpm-agents
  [... same as above ...]

  Agents (5):
    ✓ agent-manager - Manage and improve agent definitions
    ✓ rust-engineer - Specialized Rust development agent
    ✓ espocrm-developer - EspoCRM development expert
    ✓ data-analyst - Data analysis and visualization
    ✓ devops-engineer - DevOps and infrastructure automation
```

---

### `remove` - Remove Agent Source

Remove an agent source from configuration.

**Syntax:**
```bash
claude-mpm agent-source remove <source-id> [OPTIONS]
```

**Arguments:**
- `source-id` - Source identifier (required)
  - Format: `owner/repo` or `owner/repo/subdirectory`

**Options:**
- `--force` - Skip confirmation prompt
  - Use carefully to avoid accidental removal

**Examples:**

```bash
# Remove with confirmation
claude-mpm agent-source remove experimental/agents

# Remove without confirmation
claude-mpm agent-source remove experimental/agents --force
```

**Confirmation prompt:**

```
Remove agent source 'experimental/agents'?
  URL: https://github.com/experimental/agents
  Priority: 200
  Agents: 3

This will remove the source configuration but keep cached agents.
Continue? [y/N]:
```

**Effect:**
- Source removed from `agent-sources.yaml`
- Cached agents remain in filesystem (for recovery)
- Deployed agents remain active (must undeploy manually)
- Source can be re-added later with same or different settings

**Important notes:**
- Does NOT remove deployed agents
- Does NOT delete cache directory
- Use `claude-mpm agents undeploy <agent>` to remove deployed agents

---

## Agent Improvement Workflow

The agent sources system enables collaboration on agent definitions. Use the **agent-manager** agent to propose improvements.

### Using the Agent-Manager Agent

The agent-manager agent (available in the official repository) helps you:
- Analyze existing agent definitions
- Propose improvements and optimizations
- Create pull requests to agent repositories
- Test agent changes locally before contributing

**Setup:**

```bash
# 1. Add official repository (if not already added)
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents

# 2. Sync agents
claude-mpm agent-source update

# 3. Deploy agent-manager
claude-mpm agents deploy agent-manager

# 4. Start agent-manager session
claude /agent agent-manager
```

### Contributing Agent Improvements

**Workflow:**

1. **Identify Improvement Area**
   - Use an agent and identify gaps or issues
   - Check existing agent with `show` command
   - Document desired improvements

2. **Develop Improvements Locally**
   ```bash
   # Fork repository and clone
   git clone https://github.com/yourusername/claude-mpm-agents
   cd claude-mpm-agents

   # Create feature branch
   git checkout -b improve-engineer-agent

   # Edit agent markdown file
   vim agents/engineer.md
   ```

3. **Test Changes Locally**
   ```bash
   # Add local repository as source with high priority
   claude-mpm agent-source add file:///path/to/local/repo \
     --priority 1 \
     --subdirectory agents

   # Deploy and test
   claude-mpm agents deploy engineer --force
   claude /agent engineer
   ```

4. **Submit Pull Request**
   ```bash
   # Commit changes
   git add agents/engineer.md
   git commit -m "feat(engineer): improve debugging workflow"

   # Push to fork
   git push origin improve-engineer-agent

   # Create PR on GitHub
   ```

5. **Use Agent-Manager for PR**
   - Agent-manager can help generate PR description
   - Analyzes changes and suggests improvements
   - Validates agent format before submission

### Agent Review Process

**For repository maintainers:**

1. Review PR for:
   - Agent format compliance
   - Clear and concise instructions
   - No sensitive information embedded
   - Proper documentation of changes

2. Test agent locally:
   ```bash
   # Add PR branch as source for testing
   claude-mpm agent-source add https://github.com/contributor/fork \
     --subdirectory agents \
     --priority 1

   claude-mpm agent-source update
   claude-mpm agents deploy <agent-name> --force
   ```

3. Request changes or merge

---

## Troubleshooting

### Network Timeout Issues

**Symptom:** Agent source update times out or hangs.

**Causes:**
- Slow network connection
- Large repository size
- GitHub API rate limiting
- Firewall blocking GitHub access

**Solutions:**

```bash
# 1. Check network connectivity
ping github.com
curl -I https://github.com

# 2. Run diagnostics
claude-mpm doctor --checks agent-sources --verbose

# 3. Use --force to bypass cache issues
claude-mpm agent-source update --force

# 4. Check GitHub status
# Visit: https://www.githubstatus.com/

# 5. Verify firewall/proxy settings
# Ensure GitHub.com is accessible
```

**Prevention:**
- Use stable network connection
- Consider local mirror for large repos
- Update during off-peak hours

---

### Git Authentication Failures

**Symptom:** `Authentication failed` or `Permission denied` errors.

**Causes:**
- Private repositories without credentials
- Expired access tokens
- SSH key authentication (not supported)

**Solutions:**

```bash
# 1. Use HTTPS URLs (not SSH)
# ✓ Correct: https://github.com/owner/repo
# ✗ Wrong: git@github.com:owner/repo.git

# 2. For private repos, use personal access token
# Add token to URL:
claude-mpm agent-source add \
  https://YOUR_TOKEN@github.com/owner/private-repo

# 3. Verify repository accessibility
curl -I https://github.com/owner/repo

# 4. Check repository permissions
# Ensure repository is public or you have access
```

**Security note:** Store tokens securely, never commit them to version control.

---

### Priority Conflicts

**Symptom:** Wrong agent version deployed, unexpected agent behavior.

**Causes:**
- Multiple sources with same priority
- Multiple sources providing same agent name
- Priority order misunderstanding

**Diagnosis:**

```bash
# 1. Check priority configuration
claude-mpm agent-source list --by-priority

# 2. Show agent source details
claude-mpm agent-source show <source-id> --agents

# 3. Run conflict detection
claude-mpm doctor --checks agent-sources --verbose

# 4. Check which agent is actually deployed
claude-mpm agents list-deployed
```

**Solutions:**

```bash
# 1. Set distinct priorities
# Remove and re-add with different priorities
claude-mpm agent-source remove source1
claude-mpm agent-source add <url1> --priority 10

claude-mpm agent-source remove source2
claude-mpm agent-source add <url2> --priority 50

# 2. Disable conflicting source temporarily
claude-mpm agent-source disable source2

# 3. Use project-local override
# Copy agent to .claude-mpm/agents/ for absolute priority
cp ~/.claude-mpm/agent-sources/source1/agent.md \
   .claude-mpm/agents/agent.md

# 4. Redeploy with --force to ensure latest
claude-mpm agents deploy <agent-name> --force
```

**Best practice:** Use distinct priority ranges for different source types (see [Priority System](#priority-system)).

---

### Agent Discovery Issues

**Symptom:** Agent not found, `agents available` doesn't show expected agents.

**Causes:**
- Source not synced
- Source disabled
- Agent file format invalid
- Cache outdated

**Diagnosis:**

```bash
# 1. List sources and check enabled status
claude-mpm agent-source list

# 2. Update sources
claude-mpm agent-source update --force

# 3. Show source details with agents
claude-mpm agent-source show <source-id> --agents

# 4. Check cache directory
ls -la ~/.claude-mpm/agent-sources/<source-id>/

# 5. Run full diagnostics
claude-mpm doctor --checks agent-sources --verbose
```

**Solutions:**

```bash
# 1. Enable disabled source
claude-mpm agent-source enable <source-id>

# 2. Force sync
claude-mpm agent-source update --force

# 3. Verify agent file format
# Check agent markdown follows specification
cat ~/.claude-mpm/agent-sources/<source-id>/<agent>.md

# 4. Clear cache and re-sync
rm -rf ~/.claude-mpm/agent-sources/<source-id>/
claude-mpm agent-source update <source-id>
```

---

### Doctor Diagnostic Interpretation

Use `doctor` command for comprehensive agent source health checks:

```bash
# Run agent sources check
claude-mpm doctor --checks agent-sources --verbose
```

**Check categories:**

1. **Configuration File Exists**
   - Verifies `~/.claude-mpm/agent-sources.yaml` exists
   - Fix: Run `claude-mpm agent-source add` to create

2. **Configuration Valid**
   - Validates YAML syntax
   - Fix: Edit file manually or recreate

3. **Sources Configured**
   - Checks if at least one source configured
   - Fix: Add a source with `agent-source add`

4. **Sources Reachable**
   - Tests network connectivity to repositories
   - Fix: Check network, GitHub status, URLs

5. **Cache Directory Accessible**
   - Verifies cache directory writable
   - Fix: Check permissions on `~/.claude-mpm/agent-sources/`

6. **Priority Conflicts**
   - Detects duplicate priorities
   - Fix: Reassign priorities to be distinct

7. **Agents Discovered**
   - Confirms agents found in sources
   - Fix: Run `agent-source update`, check source content

**Example diagnostic output:**

```
Agent Sources Health Check:

✓ Configuration file exists
✓ Configuration valid
✓ Sources configured (2 sources)
⚠ Source reachability
  └─ myteam/agents - Network timeout
✓ Cache directory accessible
⚠ Priority conflicts detected
  └─ Sources 'team/agents' and 'community/agents' both use priority 50
✓ Agents discovered (8 agents total)

Status: Warning - 2 issues need attention
```

---

### Common Error Messages

**Error: `Source already configured`**

**Cause:** Attempting to add duplicate source.

**Solution:**
```bash
# Check existing sources
claude-mpm agent-source list

# Remove old source first
claude-mpm agent-source remove <source-id>

# Re-add with new settings
claude-mpm agent-source add <url> --priority <new-priority>
```

---

**Error: `Invalid Git URL format`**

**Cause:** URL doesn't match expected format.

**Solutions:**
```bash
# ✓ Valid formats:
https://github.com/owner/repo
https://github.com/owner/repo.git
http://github.com/owner/repo

# ✗ Invalid formats:
git@github.com:owner/repo.git  # SSH not supported
github.com/owner/repo          # Missing protocol
/local/path/to/repo            # Local paths not supported (use file://)
```

---

**Error: `Failed to fetch repository`**

**Cause:** Network error, invalid URL, or private repository.

**Solutions:**
```bash
# 1. Verify URL manually
curl -I https://github.com/owner/repo

# 2. Check GitHub status
# Visit: https://www.githubstatus.com/

# 3. For private repos, use token
claude-mpm agent-source add \
  https://TOKEN@github.com/owner/private-repo

# 4. Check network/firewall
ping github.com
```

---

**Error: `No agents found in source`**

**Cause:** Source subdirectory doesn't contain agent markdown files.

**Solutions:**
```bash
# 1. Verify subdirectory path
claude-mpm agent-source show <source-id>

# 2. Check repository structure
# Browse repository on GitHub
# Confirm agent files exist in subdirectory

# 3. Remove and re-add with correct subdirectory
claude-mpm agent-source remove <source-id>
claude-mpm agent-source add <url> --subdirectory correct/path

# 4. Update with force
claude-mpm agent-source update --force
```

---

## Best Practices

### Source Organization

**Recommended setup:**

```bash
# 1. Official/trusted sources (low priority numbers)
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents \
  --priority 50

# 2. Organization sources (very low priority numbers)
claude-mpm agent-source add https://github.com/myorg/agents \
  --priority 10

# 3. Experimental sources (high priority numbers, disabled by default)
claude-mpm agent-source add https://github.com/experimental/agents \
  --priority 200 \
  --disabled
```

**Priority strategy:**
- 1-20: Critical organization sources (overrides everything)
- 21-50: Trusted community sources
- 51-100: Standard community sources (default range)
- 101-200: Experimental/testing sources
- 201+: Low-priority fallbacks

---

### Update Frequency

**Recommendations:**

- **Daily**: Organizations with active agent development
- **Weekly**: Teams using community agents regularly
- **Monthly**: Stable setups with infrequent agent changes
- **On-demand**: Before deploying new agents

**Automation (coming soon):**
```bash
# Not yet implemented - planned feature
claude-mpm agent-source auto-update --schedule weekly
```

**Manual workflow:**

```bash
# Add to cron or task scheduler
0 9 * * 1 claude-mpm agent-source update --force  # Weekly Monday 9am
```

---

### Security Considerations

**Source verification:**
- Only add sources from trusted organizations
- Review repository contents before adding
- Check repository ownership and maintainers
- Verify HTTPS (not HTTP) URLs

**Agent review:**
- Review agent files before deployment
- Check for embedded credentials or secrets
- Validate agent instructions for safety
- Test agents in isolated environment first

**Access control:**
- Use organization repositories for team-specific agents
- Leverage GitHub repository permissions
- Consider private repositories for sensitive agents
- Rotate access tokens regularly

**Example secure workflow:**

```bash
# 1. Review repository on GitHub first
# Browse to https://github.com/org/agents
# Review agent files, maintainers, recent commits

# 2. Add source
claude-mpm agent-source add https://github.com/org/agents \
  --priority 10

# 3. Sync and review agents
claude-mpm agent-source update
claude-mpm agent-source show org/agents --agents

# 4. Test individual agent before team deployment
claude-mpm agents deploy test-agent
# Test thoroughly

# 5. Document trusted sources
echo "org/agents - Verified 2025-11-30" >> .claude-mpm/trusted-sources.txt
```

---

### Performance Optimization

**Cache management:**
```bash
# Cache is automatic, but you can clear if needed
rm -rf ~/.claude-mpm/agent-sources/<source-id>/
claude-mpm agent-source update <source-id>
```

**Selective sync:**
```bash
# Update only specific source instead of all
claude-mpm agent-source update myteam/agents
```

**Disable unused sources:**
```bash
# Keep configured but disabled
claude-mpm agent-source disable experimental/agents
```

---

## Advanced Topics

### Multiple Environments

Use different configurations for different environments:

```bash
# Development: Use experimental sources
export CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-dev
claude-mpm agent-source add https://github.com/experimental/agents \
  --priority 10

# Production: Use stable sources only
export CLAUDE_MPM_CONFIG_DIR=~/.claude-mpm-prod
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents \
  --priority 50
```

---

### Project-Local Overrides

Override agents at project level (highest priority):

```bash
# Copy agent from source to project
cp ~/.claude-mpm/agent-sources/source/agent.md \
   .claude-mpm/agents/agent.md

# Edit for project-specific needs
vim .claude-mpm/agents/agent.md

# Deploy (project version takes precedence)
claude-mpm agents deploy agent
```

**Use cases:**
- Project-specific agent customization
- Testing agent changes before contributing
- Temporary agent modifications
- Team-specific workflow adaptations

---

### Source Mirroring

For organizations with restricted internet access:

```bash
# 1. Mirror repository internally
git clone https://github.com/bobmatnyc/claude-mpm-agents
cd claude-mpm-agents
git push https://git.internal.company.com/agents/claude-mpm-agents

# 2. Add internal mirror as source
claude-mpm agent-source add \
  https://git.internal.company.com/agents/claude-mpm-agents \
  --priority 50

# 3. Update from internal mirror
claude-mpm agent-source update
```

---

### Configuration File Format

Agent sources configuration stored in: `~/.claude-mpm/agent-sources.yaml`

**Example configuration:**

```yaml
# Agent sources configuration
# Version: 1.0

repositories:
  - url: https://github.com/myteam/agents
    subdirectory: agents
    enabled: true
    priority: 10
    last_synced: "2025-11-30T14:30:00"
    etag: "W/\"abc123\""

  - url: https://github.com/bobmatnyc/claude-mpm-agents
    subdirectory: null
    enabled: true
    priority: 100
    last_synced: "2025-11-30T14:25:00"
    etag: "W/\"def456\""

  - url: https://github.com/experimental/agents
    subdirectory: agents
    enabled: false
    priority: 200
    last_synced: null
    etag: null
```

**Manual editing:**
- Not recommended (use CLI commands instead)
- If editing manually, validate YAML syntax
- Backup before editing: `cp agent-sources.yaml agent-sources.yaml.backup`
- Run `claude-mpm doctor --checks agent-sources` after editing

---

## Related Documentation

### User Documentation
- **[User Guide](user-guide.md)** - Complete Claude MPM user guide
- **[Getting Started](../getting-started/README.md)** - Installation and setup
- **[Troubleshooting](troubleshooting.md)** - General troubleshooting guide
- **[Skills Guide](skills-guide.md)** - Skills system (similar to agent sources)

### Reference Documentation
- **[Agent Sources API](../reference/agent-sources-api.md)** - Technical API reference
- **[CLI Doctor](../reference/cli-doctor.md)** - Doctor command reference
- **[Configuration](../configuration/reference.md)** - Configuration file reference

### Developer Documentation
- **[Contributing](../../CONTRIBUTING.md)** - How to contribute
- **[Architecture](../developer/README.md)** - System architecture

---

## Feedback and Support

**Found an issue?**
- Report bugs: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- Ask questions: [GitHub Discussions](https://github.com/bobmatnyc/claude-mpm/discussions)

**Have a feature request?**
- Propose enhancements via GitHub Issues
- Join community discussions

**Need help?**
1. Check [Troubleshooting](#troubleshooting) section
2. Run `claude-mpm doctor --checks agent-sources --verbose`
3. Search [GitHub Discussions](https://github.com/bobmatnyc/claude-mpm/discussions)
4. Ask in community channels

---

**Version:** 4.26.5 (2025-11-30)
**Related Ticket:** [1M-442 - Agent git sources configured but not syncing or loading](https://linear.app/workspace/issue/1M-442)
