# Agent Deployment Behavior Changes

## Summary
Modified claude-mpm to always deploy agents at the project level in the `.claude` directory, while maintaining discovery from both user and project `.claude-mpm` directories.

## Changes Made

### 1. AgentsDirectoryResolver (`src/claude_mpm/services/agents/deployment/agents_directory_resolver.py`)
- **Modified**: `determine_agents_directory` method (lines 33-62)
- **Change**: Always returns `self.working_directory / ".claude" / "agents"` regardless of agent source
- **Impact**: All agents (system, user, project) now deploy to project directory

### 2. SystemInstructionsDeployer (`src/claude_mpm/services/agents/deployment/system_instructions_deployer.py`)
- **Modified**: `deploy_system_instructions` method (lines 92-119)
- **Change**: Always uses `self.working_directory / ".claude"` for deployment
- **Impact**: System instructions always deploy to project level

### 3. CLI Agent Manager (`src/claude_mpm/cli/commands/agent_manager.py`)
- **Modified**: `_deploy_agent` method (lines 180-213)
- **Changes**:
  - Default tier changed from 'user' to 'project'
  - Always uses `Path.cwd() / ".claude" / "agents"` as deploy path
  - Fixed Path object passing (was incorrectly passing string)
- **Impact**: CLI commands consistently deploy to project directory

### 4. Deployment Strategies
Modified all deployment strategies to use project directory:

#### SystemAgentDeploymentStrategy (`strategies/system_strategy.py`)
- **Modified**: `determine_target_directory` method
- **Change**: Returns project directory instead of home directory

#### UserAgentDeploymentStrategy (`strategies/user_strategy.py`)
- **Modified**: `determine_target_directory` method
- **Change**: Returns project directory instead of user home

#### ProjectAgentDeploymentStrategy (`strategies/project_strategy.py`)
- **No changes needed**: Already deploys to project directory

### 5. Pipeline Steps (`pipeline/steps/target_directory_step.py`)
- **Modified**: Fallback logic in `execute` method
- **Change**: Uses `Path.cwd() / ".claude" / "agents"` instead of home directory

### 6. Bug Fix in AgentDeploymentService (`agent_deployment.py`)
- **Fixed**: `deploy_agent` method (line 519)
- **Issue**: Was adding `.claude/agents` to a path that already contained it
- **Solution**: Removed duplicate path construction

## Behavior Changes

### Before
- System agents → Deployed to `~/.claude/agents/`
- User agents → Deployed to `~/.claude/agents/`
- Project agents → Deployed to `<project>/.claude/agents/`

### After
- System agents → Deployed to `<project>/.claude/agents/`
- User agents → Deployed to `<project>/.claude/agents/`
- Project agents → Deployed to `<project>/.claude/agents/`

## Discovery (Unchanged)
Agent discovery still works from all sources:
- System: Package templates directory
- User: `~/.claude-mpm/agents/`
- Project: `<project>/.claude-mpm/agents/`

The MultiSourceAgentDeploymentService continues to discover agents from all these locations, but they all deploy to the project level.

## Testing
Comprehensive tests verify:
1. All deployment tiers use project directory
2. Home directory is not modified
3. CLI commands work correctly
4. Multiple agents can be deployed
5. Discovery from multiple sources still functions

## Backward Compatibility
- The `--tier` parameter is maintained for backward compatibility
- Both `--tier project` and `--tier user` work but deploy to the same location
- Existing code that depends on tier specification will continue to work

## Benefits
1. **Consistency**: All agents in one location per project
2. **Isolation**: Projects don't affect user's home directory
3. **Simplicity**: No confusion about where agents are deployed
4. **Portability**: Project-specific agents stay with the project

## Migration Notes
For existing installations:
- Agents previously deployed to `~/.claude/agents/` remain there
- New deployments go to project directory
- Consider manually moving user agents to projects if needed