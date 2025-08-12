# Project-Level Agent Support

## Overview

Claude MPM now supports project-level agents with the highest precedence in the agent hierarchy. This allows projects to customize or override system and user agents with project-specific implementations.

**Important**: Project agents in `.claude-mpm/agents/` must be in **JSON format only** (Claude MPM native format). During deployment, these JSON agents are automatically converted to Markdown format and placed in `.claude/agents/` for Claude Code compatibility.

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

2. Add your agent definition file (JSON format only):
   ```bash
   # Example: Custom engineer agent
   cat > .claude-mpm/agents/engineer.json << 'EOF'
   {
     "agent_id": "engineer",
     "version": "2.0.0",
     "metadata": {
       "name": "Project Engineer Agent",
       "description": "Project-specific engineer agent"
     },
     "capabilities": {
       "model": "claude-sonnet-4-20250514",
       "tools": ["custom_tool", "project_debugger"],
       "resource_tier": "standard"
     },
     "instructions": "# Engineer Agent (Project-Specific)\n\nCustom engineer agent with project-specific knowledge."
   }
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

### Capabilities Discovery
Agent capabilities are discovered from deployed agents in `.claude/agents/` (not from source definitions in `.claude-mpm/agents/`). This ensures consistency with what Claude Code actually uses:

- **Source of Truth**: Capabilities are read from `.claude/agents/` (deployed agents)
- **Deployment Requirement**: Project agents must be deployed to appear in capabilities discovery
- **Consistency**: Capabilities match what Claude Code has access to
- **Real-time Reflection**: Shows capabilities of currently deployed versions

**Important**: Until project agents are deployed from `.claude-mpm/agents/` to `.claude/agents/`, they won't appear in capabilities listings.

#### Example: Capabilities Discovery Workflow

```bash
# 1. Create project agent with specific capabilities
cat > .claude-mpm/agents/custom_engineer.json << 'EOF'
{
  "agent_id": "custom_engineer",
  "capabilities": {
    "tools": ["project_linter", "custom_debugger", "performance_profiler"],
    "model": "claude-sonnet-4-20250514"
  },
  "instructions": "Custom engineer with project-specific tools..."
}
EOF

# 2. Agent exists in source but not yet visible in capabilities
./claude-mpm agents list --deployed  # custom_engineer not shown

# 3. Deploy to make capabilities discoverable
./claude-mpm agents deploy

# 4. Now capabilities are discoverable from deployed version
./claude-mpm agents list --deployed  # custom_engineer now appears
./claude-mpm agents view custom_engineer  # shows deployed capabilities
```

### Cache Behavior
- Project agents are cached like other agents
- Cache automatically invalidates when project agent files change
- Force refresh available via `discover_agents(force_refresh=True)`

### File Format Requirements
- **JSON only** (`.json`) - Claude MPM structured agent definitions
- **Note**: During deployment, JSON agents are automatically converted to Markdown with YAML frontmatter and placed in `.claude/agents/` for Claude Code compatibility

## Example Project Structure

```
my-project/
├── .claude-mpm/
│   └── agents/                  # JSON format only (Claude MPM)
│       ├── engineer.json        # Override system engineer
│       ├── architect.json       # Override system architect
│       ├── payment_processor.json # Project-specific agent
│       └── api_integrator.json  # Project-specific agent
├── .claude/
│   └── agents/                  # Generated Markdown (Claude Code)
│       ├── engineer.md          # Auto-generated from JSON
│       ├── architect.md         # Auto-generated from JSON
│       ├── payment_processor.md # Auto-generated from JSON
│       └── api_integrator.md    # Auto-generated from JSON
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

1. **Version Control**: Include `.claude-mpm/agents/` (JSON source) in version control to share project agents with team
2. **Format Consistency**: Always use JSON format in `.claude-mpm/agents/` - the system handles conversion to Markdown
3. **Documentation**: Document why project-specific agents are needed
4. **Naming**: Use descriptive names that indicate project customization
5. **Testing**: Test project agents thoroughly before deployment
6. **Deployment**: Let the system auto-convert JSON to Markdown - don't manually edit `.claude/agents/*.md` files
7. **Maintenance**: Keep JSON source agents updated with framework changes

## Migration Path

To migrate existing customizations to project agents:

1. Identify customized user agents specific to a project
2. Move them to project agents directory
3. Update any project-specific instructions
4. Test the migration with `test_project_agent_precedence.py`

## Troubleshooting

### Agent Not Found
- Verify file is in `.claude-mpm/agents/` directory
- Check file extension is `.json` (only JSON format supported in this directory)
- Ensure file name follows naming conventions
- Run deployment if needed to generate `.claude/agents/*.md` files

### Wrong Agent Version Loaded
- Check tier precedence with `registry.get_agent(name).tier`
- Use `force_refresh=True` to bypass cache
- Verify no naming conflicts

### Cache Issues
- Force refresh: `registry.discover_agents(force_refresh=True)`
- Clear cache: `registry.invalidate_cache()`
- Check file permissions on agent files