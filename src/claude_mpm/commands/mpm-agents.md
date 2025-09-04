# Show available agents and their versions

Show all available Claude MPM agents with their versions and deployment status.

## Usage

```
/mpm-agents
```

## Description

This command lists all available Claude MPM agents, including both built-in agents and any custom agents you've created. It shows their current deployment status, version information, and capabilities.

## What This Command Does

When you run `/mpm-agents`, I will:

1. **List Available Agents**: Run `claude-mpm agents list` to show all agents
2. **Display Agent Information**:
   - Agent names and IDs
   - Brief descriptions
   - Model preferences (opus, sonnet, haiku)
   - Tool availability
   - Version information
   - Deployment status

## Output Example

The command displays agents in a formatted table showing:
- Agent name and description
- Version and model preference
- Tools available to the agent
- Current deployment status

## Implementation

To show available agents, I'll execute:
```bash
claude-mpm agents list --deployed
```

This will display all deployed agents that are currently available for use.

Alternatively, you can use these variations:
- `claude-mpm agents list --system` - Show system agents
- `claude-mpm agents list --by-tier` - Group agents by precedence tier
- `claude-mpm agents list --all` - Show all agents including undeployed