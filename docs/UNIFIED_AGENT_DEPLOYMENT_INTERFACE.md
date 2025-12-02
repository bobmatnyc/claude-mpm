# Unified Agent Deployment Interface

## Overview

The agent selection menu in `claude-mpm configure` now provides a **unified deploy/remove interface**. This redesign transforms agent selection from a deployment-only tool into a full deployment state manager.

## Key Features

### 1. Show ALL Agents
- Displays both deployed and available agents in a single list
- No longer filters out deployed agents
- BASE_AGENT is still filtered (it's a build tool, not deployable)

### 2. Pre-Selection of Deployed Agents
- Checkboxes are **pre-checked** for currently deployed agents
- Visual indicator: `[x] agent-name` means deployed
- Visual indicator: `[ ] agent-name` means available but not deployed

### 3. Simple Text Format
- Format: `"agent/path - Display Name"`
- No long descriptions in parentheses (kept it clean and scannable)
- Display name is shown if different from agent ID

### 4. Unified Deploy/Remove Actions
- **Selecting unchecked agent** = Deploy it
- **Un-selecting checked agent** = Remove it
- Single interface for both operations

### 5. Confirmation Before Changes
- Shows a preview of what will change:
  ```
  Changes to apply:
  Deploy 2 agent(s)
    + new-agent
    + another-agent
  Remove 1 agent(s)
    - old-agent

  Apply these changes? (Y/n)
  ```
- User can cancel before any changes are made

### 6. Comprehensive Summary
- Reports both deploy and remove operations:
  ```
  ✓ Deployed 2 agent(s)
  ✓ Removed 1 agent(s)
  ```
- Shows failures if any occur

## User Experience Flow

### Step 1: Open Agent Selection
```bash
claude-mpm configure
# Select "Select Agents" from menu
```

### Step 2: View Current State
```
Manage Agent Deployment
Checked = Deployed | Unchecked = Not Deployed
Use arrow keys to navigate, space to select/unselect, Enter to apply changes

? Agents: (Use arrow keys to navigate, Space to select, Enter to submit)
 [x] engineer - Backend Engineer
 [ ] qa - QA Engineer
 [x] pm - Project Manager
 [ ] data-engineer - Data Engineer
```

### Step 3: Make Changes
- Use arrow keys to navigate
- Press space to select/unselect
- Selected (checked) = will be deployed
- Unselected (unchecked) = will be removed or not deployed

### Step 4: Review Changes
```
Changes to apply:
Deploy 2 agent(s)
  + qa
  + data-engineer
Remove 1 agent(s)
  - engineer

Apply these changes? (Y/n)
```

### Step 5: See Results
```
✓ Deployed: qa
✓ Deployed: data-engineer
✓ Removed: engineer

✓ Deployed 2 agent(s)
✓ Removed 1 agent(s)
```

## Technical Implementation

### Location
**File**: `src/claude_mpm/cli/commands/configure.py`
**Method**: `_deploy_agents_individual()` (lines ~995-1150)

### Key Components

#### 1. Agent Discovery
```python
from claude_mpm.utils.agent_filters import (
    filter_base_agents,
    get_deployed_agent_ids,
)

# Get ALL agents (filter BASE_AGENT but keep deployed agents visible)
all_agents = filter_base_agents([...])
deployed_ids = get_deployed_agent_ids()
```

#### 2. Pre-Selection Logic
```python
# Pre-check if deployed
is_deployed = agent.name in deployed_ids

agent_choices.append(
    questionary.Choice(
        title=choice_text,
        value=agent.name,
        checked=is_deployed  # PRE-SELECT deployed agents
    )
)
```

#### 3. Diff Calculation
```python
# Convert to sets for comparison
selected_set = set(selected_agent_ids)
deployed_set = deployed_ids

# Determine actions
to_deploy = selected_set - deployed_set    # Selected but not deployed
to_remove = deployed_set - selected_set    # Deployed but not selected
```

#### 4. Execution
```python
# Deploy new agents
for agent_id in to_deploy:
    agent = agent_map.get(agent_id)
    if agent and self._deploy_single_agent(agent, show_feedback=False):
        deploy_success += 1

# Remove agents
for agent_id in to_remove:
    # Remove from project, legacy, and user locations
    for path in [project_path, legacy_path, user_path]:
        if path.exists():
            path.unlink()
```

### Deployment Locations

Agents are checked/removed in three locations:
1. **Project level**: `.claude-mpm/agents/`
2. **Legacy project**: `.claude/agents/`
3. **User level**: `~/.claude/agents/`

## Benefits

### For Users
- **Single interface** for all deployment operations
- **Visual state** - see what's deployed at a glance
- **Undo capability** - unselect to remove
- **No confusion** - deployed agents don't disappear from list

### For Developers
- **Code reduction** - unified interface eliminates duplicate logic
- **Maintainability** - single source of truth for deployment state
- **Testability** - clear input/output behavior

## Success Criteria

✅ Checkbox shows ALL agents (deployed + available)
✅ Deployed agents are pre-checked
✅ Selecting unchecked agent = deploys it
✅ Un-selecting checked agent = removes it
✅ Text format: `"agent/path - Display Name"`
✅ Confirmation before changes
✅ Summary shows both deploys and removals

## Testing

### Automated Tests
Located in: `tests/test_agent_deployment_unified_interface.py`

Tests verify:
- BASE_AGENT filtering
- All agents shown including deployed
- Pre-selection logic
- Deploy/remove set calculation
- Confirmation workflow
- Esc handling
- Summary reporting

Run tests:
```bash
pytest tests/test_agent_deployment_unified_interface.py -v
```

### Manual Testing
```bash
# 1. Deploy some agents
claude-mpm configure
# Select "Select Agents", choose a few, confirm

# 2. Run again and verify pre-selection
claude-mpm configure
# Select "Select Agents"
# Verify previously deployed agents are checked

# 3. Test removal
# Uncheck a deployed agent, check an available agent
# Confirm changes
# Verify both operations succeeded
```

## Edge Cases Handled

1. **Esc key**: Returns to menu without changes
2. **No changes**: Detects when selection matches current state
3. **User cancels**: Confirmation can be declined
4. **Missing agents**: Handles agents that don't exist on disk
5. **Multiple locations**: Checks all deployment locations for cleanup

## Future Enhancements

Potential improvements:
- Bulk operations (deploy all, remove all)
- Agent groups/presets from this interface
- Search/filter within the checkbox list
- Agent dependency indicators
- Deployment status badges (user vs project level)

## Related Documentation

- `docs/AGENTS_MANAGE_REDIRECT.md` - Agent management redirects
- `docs/research/agent-config-consolidation-2025-12-01.md` - Agent config architecture
- `src/claude_mpm/utils/agent_filters.py` - Agent filtering utilities

## Version History

- **2025-12-02**: Initial implementation of unified interface
- **Previous**: Separate deploy-only interface with deployed agents hidden
