# User Agent Cleanup Feature

## Overview

Starting from version 4.0.33, Claude MPM automatically cleans up outdated user agents during deployment when higher version agents are available from project or system sources.

## How It Works

### Version Comparison

During agent deployment, the system:
1. Discovers agents from all sources (system, project, user)
2. Compares versions across all sources
3. Selects the highest version for deployment
4. **NEW**: Removes outdated user agents that have been superseded

### Cleanup Rules

User agents are removed when:
- A project or system agent exists with the same name
- The project/system agent has a **strictly higher** version
- The user agent file is located in `~/.claude-mpm/agents/`

User agents are preserved when:
- They have the same or higher version than project/system agents
- They are unique (no project/system agent with the same name exists)
- They represent user customizations worth keeping

### Safety Measures

The cleanup process includes multiple safety checks:
- Only removes files from `~/.claude-mpm/agents/` directory
- Verifies file paths before deletion
- Logs all removal actions for audit trail
- Handles permission errors gracefully
- Can be disabled via configuration

## Configuration

### Disabling Cleanup

You can disable the cleanup feature in several ways:

#### Via Environment Variable
```bash
export CLAUDE_MPM_CLEANUP_USER_AGENTS=false
claude-mpm deploy-agents
```

#### Via Configuration File
Add to your `claude-mpm.yml`:
```yaml
agent_deployment:
  cleanup_outdated_user_agents: false
```

## Example Scenarios

### Scenario 1: Project Update
```
System: engineer v2.0.0
Project: engineer v2.5.0 (updated)
User: engineer v2.1.0 (previously copied)
Result: User agent removed, project v2.5.0 deployed
```

### Scenario 2: User Customization
```
System: qa v1.5.0
User: qa v2.0.0 (user customized)
Result: User agent preserved and deployed
```

### Scenario 3: User-Only Agent
```
User: custom-tool v1.0.0 (no system/project version)
Result: User agent preserved and deployed
```

## Deployment Output

When cleanup occurs, you'll see messages like:
```
INFO: Removing outdated user agent: engineer v2.1.0 (superseded by project v2.5.0)
INFO: Cleanup complete: removed 2 outdated user agents
```

## Troubleshooting

### Permission Errors
If you see permission errors during cleanup:
- Check file ownership in `~/.claude-mpm/agents/`
- Run with appropriate permissions
- Or disable cleanup temporarily

### Preserving Specific Agents
To prevent specific user agents from being removed:
- Ensure they have version numbers >= project/system versions
- Or disable cleanup before deployment

## Best Practices

1. **Version Management**: Keep user agent versions updated when customizing
2. **Regular Cleanup**: Allow automatic cleanup to prevent accumulation of outdated agents
3. **Backup Important Customizations**: Before major updates, backup custom user agents
4. **Monitor Logs**: Review deployment logs to understand what was cleaned up

## Technical Details

The cleanup logic is implemented in:
- `MultiSourceAgentDeploymentService.cleanup_outdated_user_agents()`
- Only runs during multi-source deployment mode
- Integrates with existing version comparison logic
- Respects all existing deployment configurations