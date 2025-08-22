# Agent Manager Guide

## Overview

The Agent Manager is a comprehensive tool for creating, customizing, and managing agents across the Claude MPM framework's three-tier hierarchy. It provides full lifecycle management from agent creation through deployment and maintenance.

## Agent Hierarchy

Claude MPM uses a three-tier agent hierarchy with clear precedence:

1. **Project Level** (`.claude/agents/`) - Highest priority
   - Project-specific agents that override all others
   - Deployed per-project for custom workflows
   - Persists with project repository

2. **User Level** (`~/.claude/agents/`) - Middle priority
   - User's personal agent collection
   - Shared across all projects for that user
   - Overrides system agents but not project agents

3. **System Level** (Framework installation) - Lowest priority
   - Default agents shipped with claude-mpm
   - Available to all users and projects
   - Can be overridden at user or project level

## Getting Started

### List Available Agents

View all agents across the three tiers:

```bash
claude-mpm agent-manager list
```

This shows agents with tier indicators:
- `[P]` - Project level agents
- `[U]` - User level agents
- `[S]` - System level agents

### List Agent Templates

View all available agent templates that can be used as starting points:

```bash
claude-mpm agent-manager templates
```

## Creating Agents

### Interactive Creation

The easiest way to create an agent is using the interactive wizard:

```bash
claude-mpm agent-manager create
```

You'll be prompted for:
- Agent ID (lowercase, hyphens only)
- Display name
- Description
- Model selection (sonnet/opus/haiku)
- Tool choice strategy

### Command-Line Creation

Create an agent with command-line arguments:

```bash
claude-mpm agent-manager create \
  --id my-agent \
  --name "My Custom Agent" \
  --description "Specialized agent for my tasks" \
  --model sonnet \
  --tool-choice auto
```

### Using Templates

Create an agent based on an existing template:

```bash
claude-mpm agent-manager create \
  --id my-engineer \
  --template engineer \
  --name "My Engineering Agent"
```

## Creating Agent Variants

Variants allow you to create specialized versions of existing agents:

```bash
claude-mpm agent-manager variant \
  --base research \
  --id research-web \
  --name "Web Research Specialist" \
  --instructions "Focus on web technologies and modern frameworks"
```

## Deploying Agents

### Deploy to User Level

Deploy an agent to your personal collection:

```bash
claude-mpm agent-manager deploy --id my-agent --tier user
```

### Deploy to Project Level

Deploy an agent to the current project:

```bash
claude-mpm agent-manager deploy --id my-agent --tier project
```

## Customizing PM Instructions

The Project Manager (PM) instructions control how work is delegated to agents.

### User-Level PM Customization

Edit your global PM instructions:

```bash
claude-mpm agent-manager customize-pm --level user
```

This creates/edits `~/.claude-mpm/INSTRUCTIONS.md`

### Project-Level PM Customization

Edit project-specific PM instructions:

```bash
claude-mpm agent-manager customize-pm --level project
```

This creates/edits `./.claude-mpm/INSTRUCTIONS.md`

### Custom Delegation Patterns

Add specific delegation patterns:

```bash
claude-mpm agent-manager customize-pm \
  --patterns "Always delegate testing to QA agent" \
             "Use Engineer for all code changes" \
  --rules "Never skip code review" \
          "Always run tests before deployment"
```

## Viewing Agent Details

Get detailed information about a specific agent:

```bash
claude-mpm agent-manager show --id engineer
```

This displays:
- Agent configuration
- Instruction content
- Metadata and capabilities
- Deployment information
- Override chain (if applicable)

## Testing Agent Configuration

Validate an agent configuration before deployment:

```bash
claude-mpm agent-manager test --id my-agent
```

This checks:
- JSON structure validity
- Instruction file existence
- ID conflicts
- Model availability
- Deployment simulation

## Agent Configuration Structure

Agents are defined using JSON configuration files:

```json
{
  "id": "agent-id",
  "name": "Agent Display Name",
  "prompt": "agent-instructions.md",
  "model": "sonnet",
  "tool_choice": "auto",
  "metadata": {
    "description": "Agent purpose and capabilities",
    "version": "1.0.0",
    "capabilities": ["capability1", "capability2"],
    "tags": ["tag1", "tag2"],
    "author": "Creator Name",
    "category": "engineering"
  }
}
```

### Configuration Fields

- **id**: Unique identifier (lowercase, hyphens only)
- **name**: Display name shown in interfaces
- **prompt**: Markdown file with agent instructions
- **model**: LLM model (sonnet/opus/haiku)
- **tool_choice**: How tools are selected (auto/required/any/none)
- **metadata**: Additional agent information

## Best Practices

### Agent Creation
- Use descriptive, purposeful IDs
- Write clear, focused instructions
- Include comprehensive metadata
- Test before deploying to production

### Variant Management
- Document variant purpose clearly
- Maintain minimal override sets
- Track variant lineage
- Test inheritance chain

### PM Customization
- Keep instructions focused and clear
- Document custom workflows
- Test delegation patterns
- Version control .claude-mpm/INSTRUCTIONS.md files

**Important File Distinctions**:
- `CLAUDE.md` - Development guidelines (read automatically by Claude Code)
- `.claude-mpm/INSTRUCTIONS.md` - PM customization and delegation rules
- These serve different purposes and should not be confused

### Deployment Strategy
- Start with user level for testing
- Deploy to project for team sharing
- Reserve system level for stable agents
- Always backup before overriding

## Common Use Cases

### Creating a Specialized QA Agent

```bash
# Create a variant of the QA agent for API testing
claude-mpm agent-manager variant \
  --base qa \
  --id api-qa \
  --name "API Testing Specialist" \
  --instructions "Focus on REST API testing, response validation, and performance metrics"
```

### Setting Up Project-Specific Agents

```bash
# Navigate to your project
cd my-project

# Create project-specific agent
claude-mpm agent-manager create \
  --id project-deployer \
  --name "Project Deployment Agent" \
  --description "Handles deployment for this specific project"

# Deploy to project level
claude-mpm agent-manager deploy \
  --id project-deployer \
  --tier project
```

### Customizing Delegation Workflow

```bash
# Add project-specific delegation rules
claude-mpm agent-manager customize-pm --level project \
  --patterns "Database changes require Security review" \
             "All UI changes go through Web UI agent" \
  --rules "No direct production deployments" \
          "Require approval for breaking changes"
```

## Troubleshooting

### Agent Not Found

If an agent isn't found:
1. Check the agent ID spelling
2. Verify the agent is deployed: `claude-mpm agent-manager list`
3. Check the correct tier for the agent

### ID Conflicts

If you get an ID conflict error:
1. Use `claude-mpm agent-manager list` to see existing agents
2. Choose a unique ID
3. Consider creating a variant instead

### Deployment Failures

If deployment fails:
1. Check directory permissions
2. Ensure the target directory exists
3. Verify no file system issues
4. Try with `--force` flag if updating

### Invalid Configuration

If configuration validation fails:
1. Check JSON syntax
2. Verify all required fields are present
3. Ensure model and tool_choice values are valid
4. Test with `claude-mpm agent-manager test`

## Advanced Features

### Batch Agent Creation

Create multiple agents from a configuration file:

```bash
# Create agents.json with multiple agent definitions
# Then iterate through them with a script
for agent in $(jq -r '.agents[].id' agents.json); do
  claude-mpm agent-manager create --id "$agent" --template "$agent"
done
```

### Agent Migration

Move agents between tiers:

```bash
# Export agent configuration
claude-mpm agent-manager show --id my-agent --format json > my-agent.json

# Deploy to different tier
claude-mpm agent-manager deploy --id my-agent --tier project
```

### Backup and Restore

Always backup before major changes:

```bash
# Backup user agents
cp -r ~/.claude/agents ~/.claude/agents.backup

# Backup project agents
cp -r .claude/agents .claude/agents.backup
```

## Integration with Claude Code

The Agent Manager integrates seamlessly with Claude Code. Deployed agents are automatically available for delegation by the PM agent.

To use your custom agents:
1. Create and deploy your agent
2. Start Claude Code with `claude-mpm run`
3. The PM will automatically discover and use your agents

## Command Reference

### Main Commands

- `list` - List all agents across tiers
- `create` - Create new agent
- `variant` - Create agent variant
- `deploy` - Deploy agent to tier
- `customize-pm` - Edit PM instructions
- `show` - Display agent details
- `test` - Validate configuration
- `templates` - List available templates

### Common Options

- `--format [text|json|yaml]` - Output format
- `--tier [project|user]` - Deployment tier
- `--force` - Force operation
- `--help` - Show command help

## Conclusion

The Agent Manager provides comprehensive control over your Claude MPM agent ecosystem. By understanding the three-tier hierarchy and using the various commands effectively, you can create a customized, efficient workflow tailored to your specific needs.