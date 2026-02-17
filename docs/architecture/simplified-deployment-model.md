# Simplified Agent/Skill Deployment Model

## Overview

The simplified deployment model makes agent and skill deployment predictable and transparent. Instead of complex exclusion lists and 4-tier discovery, you now have:

1. **Explicit Configuration**: `agents.enabled` and `skills.enabled` lists in `configuration.yaml`
2. **Reconciliation**: Deploy ONLY what's configured, remove what's not
3. **Clear View**: See exactly what's configured vs deployed

## Key Concepts

### Before (Complex)
- 4-tier discovery (project, user, system, remote)
- Exclusion lists that don't match CLI output
- Unclear which agents are actually deployed
- Auto-discovery with unexpected behavior

### After (Simple)
- **Single source of truth**: `agents.enabled` list
- **Reconciliation**: Configured ⟷ Deployed
- **Predictable**: Add to list → deployed, remove from list → removed
- **Clear CLI**: Shows configured vs deployed state

## Configuration

### Example `configuration.yaml`

```yaml
agents:
  # Explicit list of agents to deploy
  enabled:
    - engineer
    - qa
    - research

  auto_discover: false  # Deprecated, use enabled list

skills:
  # Explicit list of skills
  enabled:
    - git-workflow
    - systematic-debugging

  # Auto-add skills required by enabled agents
  auto_detect_dependencies: true
```

## Workflow

### 1. Configure Agents

Edit `.claude-mpm/configuration.yaml`:

```yaml
agents:
  enabled:
    - engineer
    - qa
    - research
```

### 2. Sync Agents

Fetch agents from remote sources to cache:

```bash
claude-mpm agents sync
```

This downloads agents to `~/.claude-mpm/cache/agents/`.

### 3. View Reconciliation State

See what will be deployed/removed:

```bash
claude-mpm agents reconcile --show-only
```

Output:
```
┌─────────┬──────────────┬────────────┬────────────┐
│ Agent   │ Configured   │ Deployed   │ Action     │
├─────────┼──────────────┼────────────┼────────────┤
│ engineer│ ✓            │ ✓          │ -          │
│ qa      │ ✓            │ ✓          │ -          │
│ research│ ✓            │ ✗          │ Will deploy│
│ ops     │ ✗            │ ✓          │ Will remove│
└─────────┴──────────────┴────────────┴────────────┘
```

### 4. Perform Reconciliation

Deploy missing agents and remove unneeded ones:

```bash
claude-mpm agents reconcile
```

This:
- Copies agents from cache → `.claude/agents/`
- Removes agents NOT in `enabled` list (if MPM-managed)
- Preserves user-created agents

## Commands

### `claude-mpm agents reconcile`

Reconcile deployed agents with configuration.

**Options:**
- `--show-only`: Show reconciliation view without changes
- `--dry-run`: Alias for --show-only
- `--project-path PATH`: Target project directory

**Examples:**

```bash
# Show current state
claude-mpm agents reconcile --show-only

# Perform reconciliation
claude-mpm agents reconcile

# Reconcile for specific project
claude-mpm agents reconcile --project-path ~/my-project
```

### `claude-mpm agents sync`

Fetch agents from remote sources to cache.

```bash
# Sync all sources
claude-mpm agents sync

# Force re-sync (bypass ETag cache)
claude-mpm agents sync --force
```

### `claude-mpm agents list`

List agents with deployment status.

```bash
# Show all agents
claude-mpm agents list

# Show only deployed
claude-mpm agents list --deployed
```

## Reconciliation Logic

### Deployment Rules

1. **Deploy** agents in `agents.enabled` that aren't in `.claude/agents/`
   - Copied from `~/.claude-mpm/cache/agents/`
   - Requires prior `claude-mpm agents sync`

2. **Remove** agents in `.claude/agents/` NOT in `agents.enabled`
   - Only removes MPM-managed agents (check author marker)
   - Preserves user-created agents

3. **Unchanged** agents in both lists
   - No action taken

### MPM-Managed Detection

An agent is MPM-managed if its frontmatter contains:
- `author: claude-mpm`
- `author: 'claude-mpm'`
- `author: anthropic`

User-created agents (without these markers) are NEVER auto-removed.

## Skills

Skills follow the same model:

### Configuration

```yaml
skills:
  enabled:
    - git-workflow
    - systematic-debugging

  auto_detect_dependencies: true
```

### Auto-Dependency Detection

If `auto_detect_dependencies: true`, skills are auto-added based on:
1. Skills in `skills.enabled` list
2. Skills required by agents in `agents.enabled`

This ensures agents always have their required skills deployed.

### Commands

```bash
# Show skill reconciliation
claude-mpm skills reconcile --show-only

# Deploy configured skills
claude-mpm skills reconcile
```

## Migration from Old Model

### Step 1: Identify Current Agents

```bash
# List currently deployed agents
claude-mpm agents list --deployed
```

### Step 2: Update Configuration

Edit `.claude-mpm/configuration.yaml`:

```yaml
agents:
  enabled:
    - <agent-1>
    - <agent-2>
    # ... all agents you want

  auto_discover: false  # Disable old model
```

### Step 3: Reconcile

```bash
# View changes
claude-mpm agents reconcile --show-only

# Apply changes
claude-mpm agents reconcile
```

### Step 4: Verify

```bash
# Check deployed state
claude-mpm agents list --deployed
```

## Backward Compatibility

If `agents.enabled` is empty AND `auto_discover` is true:
- Falls back to auto-discovery mode
- Shows migration warning
- No agents are removed

This ensures existing setups continue working.

## Troubleshooting

### Agent Not Found in Cache

**Error**: "Agent 'xyz' not found in cache"

**Solution**: Run `claude-mpm agents sync` to fetch agents from sources.

### Agent Not Deploying

**Check**:
1. Agent is in `agents.enabled` list
2. Agent exists in cache: `ls ~/.claude-mpm/cache/agents/`
3. No errors in reconciliation output

### User Agent Being Removed

**Cause**: Agent has MPM author marker but isn't in `enabled` list.

**Solution**:
1. Add to `enabled` list, OR
2. Remove author marker to make it user-managed

## Architecture

### Components

1. **UnifiedConfig** (`src/claude_mpm/core/unified_config.py`)
   - `AgentConfig` with `enabled` list
   - `SkillConfig` with `enabled` list and auto-dependencies

2. **DeploymentReconciler** (`src/claude_mpm/services/agents/deployment/deployment_reconciler.py`)
   - Reconciliation logic (deploy/remove)
   - State calculation (configured vs deployed vs cached)
   - MPM-managed detection

3. **CLI Commands** (`src/claude_mpm/cli/commands/agents_reconcile.py`)
   - `agents reconcile`: Reconcile agents
   - `skills reconcile`: Reconcile skills
   - Rich tables for clear visualization

### Data Flow

```
configuration.yaml (agents.enabled)
         ↓
DeploymentReconciler
         ↓
ReconciliationState (to_deploy, to_remove, unchanged)
         ↓
Deploy: cache → .claude/agents/
Remove: .claude/agents/ (MPM only)
         ↓
Updated .claude/agents/
```

## Benefits

1. **Predictability**: Explicit list = explicit deployment
2. **Transparency**: Clear view of what's configured vs deployed
3. **Safety**: User agents never auto-removed
4. **Simplicity**: No complex exclusion logic
5. **Consistency**: Same model for agents and skills

## See Also

- [Example Configuration](../examples/configuration-simplified.yaml)
- [Agent Sync Documentation](guides/agent-synchronization.md)
- [Skill Management](guides/skills-management.md)
