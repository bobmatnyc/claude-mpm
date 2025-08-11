# Project-Level Agent Support

## Overview

Claude MPM now supports project-level agents with the highest precedence in the agent hierarchy. This allows projects to customize or override system and user agents with project-specific implementations.

## Agent Hierarchy

The agent system follows a three-tier hierarchy with the following precedence order:

1. **PROJECT** (highest precedence) - Project-specific agents in `<project>/.claude-mpm/agents/`
2. **USER** - User-level agents in `~/.claude-mpm/agents/`  
3. **SYSTEM** (lowest precedence) - System agents in framework installation

When agents with the same name exist at multiple tiers, the PROJECT version takes precedence.

## Creating Project Agents

To create a project-specific agent:

1. Create the project agents directory:
   ```bash
   mkdir -p .claude-mpm/agents
   ```

2. Add your agent definition file (`.md`, `.json`, `.yaml`):
   ```bash
   # Example: Custom engineer agent
   cat > .claude-mpm/agents/engineer.md << 'EOF'
   ---
   description: Project-specific engineer agent
   version: 2.0.0
   tools: ["custom_tool", "project_debugger"]
   ---
   
   # Engineer Agent (Project-Specific)
   
   Custom engineer agent with project-specific knowledge.
   EOF
   ```

## Use Cases

### 1. Override System Agents
Replace default system agents with project-specific versions that have:
- Custom instructions tailored to your project
- Additional tools or capabilities
- Project-specific knowledge and context

### 2. Add Project-Only Agents
Create agents that only exist for your project:
- Domain-specific agents (e.g., `payment_processor`, `inventory_manager`)
- Integration agents for project-specific services
- Specialized workflow agents

### 3. Testing Custom Agents
Develop and test new agent templates locally before promoting them to user or system level.

## Implementation Details

### Discovery Process
1. AgentRegistry scans directories in precedence order
2. Project agents directory is checked first
3. Agents are deduplicated by name, keeping highest precedence version

### Cache Behavior
- Project agents are cached like other agents
- Cache automatically invalidates when project agent files change
- Force refresh available via `discover_agents(force_refresh=True)`

### File Formats Supported
- Markdown (`.md`) - with optional YAML frontmatter
- JSON (`.json`) - structured agent definitions
- YAML (`.yaml`, `.yml`) - configuration format

## Example Project Structure

```
my-project/
├── .claude-mpm/
│   └── agents/
│       ├── engineer.md          # Override system engineer
│       ├── architect.md         # Override system architect
│       ├── payment_processor.md # Project-specific agent
│       └── api_integrator.json  # Project-specific agent
├── src/
└── README.md
```

## API Usage

```python
from claude_mpm.services.agents.registry import AgentRegistry

# Initialize registry
registry = AgentRegistry()

# Discover all agents (including project-level)
agents = registry.discover_agents()

# Get specific agent (will return project version if exists)
engineer = registry.get_agent("engineer")
if engineer.tier.value == "project":
    print("Using project-specific engineer agent")

# List only project agents
project_agents = registry.list_agents(tier=AgentTier.PROJECT)
```

## Best Practices

1. **Version Control**: Include `.claude-mpm/agents/` in version control to share project agents with team
2. **Documentation**: Document why project-specific agents are needed
3. **Naming**: Use descriptive names that indicate project customization
4. **Testing**: Test project agents thoroughly before deployment
5. **Maintenance**: Keep project agents updated with framework changes

## Migration Path

To migrate existing customizations to project agents:

1. Identify customized user agents specific to a project
2. Move them to project agents directory
3. Update any project-specific instructions
4. Test the migration with `test_project_agent_precedence.py`

## Troubleshooting

### Agent Not Found
- Verify file is in `.claude-mpm/agents/` directory
- Check file extension is supported (`.md`, `.json`, `.yaml`)
- Ensure file name follows naming conventions

### Wrong Agent Version Loaded
- Check tier precedence with `registry.get_agent(name).tier`
- Use `force_refresh=True` to bypass cache
- Verify no naming conflicts

### Cache Issues
- Force refresh: `registry.discover_agents(force_refresh=True)`
- Clear cache: `registry.invalidate_cache()`
- Check file permissions on agent files