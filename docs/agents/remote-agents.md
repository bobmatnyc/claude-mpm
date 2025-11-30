# Remote Agent Discovery

Claude MPM now supports automatic discovery and deployment of remote agents from GitHub repositories.

## Overview

Remote agents are the **3rd tier** in the 4-tier agent discovery system:

1. **System** - Built-in agents (lowest priority)
2. **User** - User-level agents (DEPRECATED, will be removed in v5.0.0)
3. **Remote** - GitHub-synced agents from cache
4. **Project** - Project-specific agents (highest priority)

## How It Works

### Automatic Synchronization

Remote agents are automatically synced from GitHub during Claude MPM startup:

1. **GitHub Sync**: Agents are fetched from configured GitHub repositories
2. **Local Caching**: Agents are cached to `~/.claude-mpm/cache/remote-agents/` as Markdown files
3. **ETag Updates**: Incremental updates using HTTP ETags (only changed files are re-downloaded)
4. **Discovery Integration**: Cached agents are automatically discovered during deployment

### Agent Priority

When multiple sources provide the same agent, the priority system determines which version is deployed:

```
Priority: PROJECT > REMOTE > USER > SYSTEM
          (highest)                 (lowest)
```

**Example**: If you have a "Security Scanner" agent in:
- System templates (v1.0.0)
- Remote cache (v1.5.0)
- Project agents (v2.0.0)

The **project version (v2.0.0)** will be deployed because project agents have the highest priority.

## Remote Agent Format

Remote agents are stored as Markdown files with metadata sections:

```markdown
# Agent Name

Agent description paragraph (appears in agent list)

## Configuration
- Model: sonnet
- Priority: 100

## Routing
- Keywords: keyword1, keyword2, keyword3
- Paths: /path1/, /path2/
```

### Markdown Structure

| Section | Required | Description |
|---------|----------|-------------|
| `# Agent Name` | Yes | First heading becomes the agent name |
| Description | No | First paragraph after heading becomes description |
| `## Configuration` | No | Agent settings (model, priority) |
| `## Routing` | No | Routing keywords and file paths |

### Supported Models

- `sonnet` (default) - Claude 3.5 Sonnet
- `opus` - Claude 3 Opus
- `haiku` - Claude 3 Haiku

### Priority Values

- `0-50` - Low priority (system agents)
- `50-100` - Medium priority (user/remote agents)
- `100-200` - High priority (specialized agents)

## Cache Management

### Cache Location

Remote agents are cached to:
```
~/.claude-mpm/cache/remote-agents/
```

Each agent has two files:
- `<agent-name>.md` - The agent content
- `<agent-name>.md.meta.json` - Metadata (version, ETag, last modified)

### Cache Updates

Cache updates happen automatically:
- **On Startup**: Claude MPM checks for agent updates
- **ETag Validation**: Only changed files are re-downloaded
- **Incremental**: Fast updates, minimal bandwidth

### Manual Cache Refresh

To force a cache refresh:
```bash
rm -rf ~/.claude-mpm/cache/remote-agents/
claude-mpm --mpm:agents deploy
```

## User-Level Deprecation

⚠️ **IMPORTANT**: User-level agents (`~/.claude-mpm/agents/`) are **DEPRECATED** and will be removed in v5.0.0.

### Why Deprecate User-Level Agents?

1. **Project Isolation**: Agents should be project-specific, not global
2. **Version Control**: Project agents can be versioned with your code
3. **Team Consistency**: All team members use the same agents
4. **Simpler Architecture**: Fewer tiers to manage

### Migration Process

Migrate user-level agents to project-level:

```bash
# 1. Dry run (see what would be migrated)
claude-mpm agents migrate-to-project --dry-run

# 2. Perform migration
claude-mpm agents migrate-to-project

# 3. Verify agents work in project
claude-mpm agents list --deployed

# 4. Remove old user-level agents
rm -rf ~/.claude-mpm/agents/
```

### Migration Command Options

```bash
claude-mpm agents migrate-to-project [OPTIONS]

Options:
  --dry-run    Show what would be migrated without actually doing it
  --force      Overwrite existing project agents if conflicts
```

## Troubleshooting

### Remote Agents Not Appearing

**Symptom**: Remote agents don't show up in `claude-mpm agents list --deployed`

**Solutions**:
1. Check cache exists: `ls ~/.claude-mpm/cache/remote-agents/`
2. Verify internet connection during startup
3. Check logs: `claude-mpm --debug`
4. Force cache refresh (see Cache Updates above)

### User-Level Deprecation Warning

**Symptom**: Seeing deprecation warnings on every startup

**Solution**: Migrate user-level agents to project-level:
```bash
claude-mpm agents migrate-to-project
```

### Agent Priority Confusion

**Symptom**: Wrong agent version is being deployed

**Solution**: Check agent priority with:
```bash
claude-mpm agents list --by-tier
```

This shows which tier each agent comes from and helps debug priority issues.

### Cache Corruption

**Symptom**: Errors during agent discovery about malformed Markdown

**Solution**: Clear and rebuild cache:
```bash
rm -rf ~/.claude-mpm/cache/remote-agents/
claude-mpm --mpm:agents deploy
```

## Best Practices

### For Individual Users

1. **Use Project Agents**: Create agents in `.claude-mpm/agents/` (project-level)
2. **Avoid User-Level**: Don't create agents in `~/.claude-mpm/agents/` (deprecated)
3. **Remote for Shared**: Use remote agents for shared team resources
4. **Override When Needed**: Override remote agents with project agents when customization is needed

### For Teams

1. **Remote Agent Repository**: Maintain a GitHub repository of shared agents
2. **Project-Level Customizations**: Override remote agents at project level when needed
3. **Version Control**: Commit project agents to version control
4. **Document Overrides**: Clearly document why project agents override remote versions

### For Framework Developers

1. **System Agents**: Keep system agents minimal (core functionality only)
2. **Remote Distribution**: Distribute specialized agents via remote repositories
3. **Documentation**: Document agent capabilities and routing rules
4. **Semantic Versioning**: Use semantic versions for agent updates

## Example Workflows

### Creating a Custom Agent

```bash
# 1. Create project agent (overrides system/remote)
cat > .claude-mpm/agents/my-agent.json <<EOF
{
  "agent_id": "my-agent",
  "metadata": {
    "name": "My Custom Agent",
    "description": "Specialized agent for my project",
    "version": "1.0.0"
  },
  "model": "sonnet",
  "routing": {
    "keywords": ["custom", "specialized"],
    "paths": ["/custom/"],
    "priority": 100
  }
}
EOF

# 2. Deploy
claude-mpm --mpm:agents deploy

# 3. Verify
claude-mpm agents list --deployed | grep "My Custom Agent"
```

### Using Remote Agents

```bash
# Remote agents are automatically discovered
# No configuration needed - just use them!

# View all available agents (including remote)
claude-mpm agents list --by-tier
```

### Overriding a Remote Agent

```bash
# 1. Check remote agent version
claude-mpm agents list --by-tier | grep "Security Scanner"

# 2. Create project override
cat > .claude-mpm/agents/security-scanner.json <<EOF
{
  "agent_id": "security-scanner",
  "metadata": {
    "name": "Security Scanner",
    "description": "Project-specific security configuration",
    "version": "2.0.0"
  },
  ...
}
EOF

# 3. Deploy (project agent will take priority)
claude-mpm --mpm:agents deploy
```

## Learn More

- [Agent Creation Guide](./creating-agents.md)
- [Agent Deployment](./deployment.md)
- [Migration Guide](./migration.md)
- [Configuration Reference](../reference/configuration.md)
