# Dynamic Agent Capabilities

The Claude MPM framework automatically generates and updates agent documentation based on the agents actually deployed in your project. This ensures that the framework's instructions always reflect the true capabilities available to Claude.

## What Are Dynamic Agent Capabilities?

When Claude MPM deploys its instructions (INSTRUCTIONS.md), it automatically discovers all available agents and generates up-to-date documentation about their capabilities. This happens transparently without any manual intervention.

## Benefits for Users

### Always Accurate Documentation
- No more outdated agent descriptions
- Documentation reflects your actual agent setup
- Project-specific customizations are automatically included

### Zero Maintenance
- No manual updates needed when agents change
- Automatic detection of new agents
- Removal of deprecated agent references

### Project Awareness
- Shows your project-specific agents separately
- Respects agent precedence (project > user > system)
- Highlights customizations you've made

## How to Verify It's Working

### Check the Generated Instructions

Look at your INSTRUCTIONS.md file for the dynamically generated section:

```markdown
## Agent Names & Capabilities
**Core Agents**: data_engineer, documentation, engineer, ops, qa, research, security, version_control

**Agent Capabilities**:
- **Data Engineer Agent**: data, etl, analytics
- **Documentation Agent**: docs, api, guides
- **Engineer Agent**: coding, architecture, implementation
[...]

*Generated from 8 deployed agents*
```

The footer "*Generated from X deployed agents*" confirms dynamic generation is active.

### View Available Agents

Use the info command to see which agents are available:

```bash
claude-mpm info
```

This will show:
- Deployed agents and their versions
- Agent source (system, user, or project)
- Current capabilities

### Monitor Agent Changes

When you add or modify agents, the documentation updates automatically on the next deployment. You can trigger a manual update:

```bash
# Redeploy framework instructions
claude-mpm deploy --force
```

## Understanding the Generated Content

### Core Agents List
Shows all available agent IDs in a comma-separated format. These are the exact names you can use in delegation commands.

### Agent Capabilities Section
For each agent, displays:
- **Agent Name**: Human-readable name
- **Key Capabilities**: Primary specializations or use cases
- **Source Tier**: Whether it's a system, user, or project agent

### Agent Name Formats
Shows both valid naming conventions:
- Capitalized format: "Research Agent", "Engineer Agent"
- Lowercase format: "research", "engineer"

## Customizing Your Agents

### Adding Project-Specific Agents

1. Create an agent in your project's agent directory
2. Follow the standard agent schema
3. The agent appears automatically in the next deployment

### Overriding System Agents

1. Create an agent with the same ID in your project
2. Your version takes precedence
3. Documentation shows your customized capabilities

## Troubleshooting

### Agents Not Appearing

If an agent isn't showing up:
1. Verify the agent file is in the correct location
2. Check the agent follows the proper schema
3. Ensure no syntax errors in the agent definition

### Outdated Information

If the documentation seems outdated:
1. Force a redeployment: `claude-mpm deploy --force`
2. Check for caching issues
3. Verify the agent files are being read correctly

### Performance Considerations

The dynamic generation adds minimal overhead:
- Discovery: ~0.6ms
- Generation: ~1.1ms
- Total: ~3.3ms

This is negligible and won't impact your workflow.

## Best Practices

1. **Regular Updates**: The system updates automatically, but you can force updates after major agent changes
2. **Agent Naming**: Use clear, descriptive agent names for better documentation
3. **Specializations**: Define clear specializations for each agent
4. **Testing**: Verify agent changes appear correctly before major deployments

## Technical Details

For developers interested in the implementation:
- Agents are discovered via the AgentRegistry
- Content is generated using Jinja2 templates
- Integration happens during the deployment phase
- Fallback mechanisms ensure system stability

The dynamic agent capabilities system ensures your Claude MPM installation always has accurate, up-to-date documentation without any manual maintenance required.