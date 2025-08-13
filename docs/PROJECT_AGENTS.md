# Project-Level Agent Support

## Overview

Claude MPM now supports project-level agents with the highest precedence in the agent hierarchy. This allows projects to customize or override system and user agents with project-specific implementations.

**Important**: Project agents in `.claude-mpm/agents/` support **multiple formats** (.json, .yaml, .yml, .md) for flexibility. During deployment, agents are automatically converted to Markdown format with YAML frontmatter and placed in `.claude/agents/` for Claude Code compatibility.

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

2. Add your agent definition file (supports JSON, YAML, or Markdown formats):
   ```bash
   # Example: Custom engineer agent (JSON format)
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
   
   # Alternative: YAML format for better readability
   cat > .claude-mpm/agents/engineer.yaml << 'EOF'
   agent_id: engineer
   version: "2.0.0"
   metadata:
     name: "Project Engineer Agent"
     description: "Project-specific engineer agent"
   capabilities:
     model: "claude-sonnet-4-20250514"
     tools: ["custom_tool", "project_debugger"]
     resource_tier: "standard"
   instructions: |
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
- **Multiple formats supported**: `.json`, `.yaml`, `.yml`, and `.md` files
- **Consistent schema**: All formats must follow the same agent schema structure
- **Note**: During deployment, all agent formats are automatically converted to Markdown with YAML frontmatter and placed in `.claude/agents/` for Claude Code compatibility

## Example Project Structure

```
my-project/
├── .claude-mpm/
│   └── agents/                  # Multiple formats supported
│       ├── engineer.json        # Override system engineer (JSON)
│       ├── architect.yaml       # Override system architect (YAML)
│       ├── payment_processor.json # Project-specific agent (JSON)
│       └── api_integrator.md    # Project-specific agent (Markdown)
├── .claude/
│   └── agents/                  # Generated Markdown (Claude Code)
│       ├── engineer.md          # Auto-generated from JSON
│       ├── architect.md         # Auto-generated from YAML
│       ├── payment_processor.md # Auto-generated from JSON
│       └── api_integrator.md    # Auto-generated from Markdown
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

1. **Version Control**: Include `.claude-mpm/agents/` (source files) in version control to share project agents with team
2. **Format Choice**: Choose the format that works best for your team - JSON for structure, YAML for readability, or Markdown for documentation-heavy agents
3. **Documentation**: Document why project-specific agents are needed
4. **Naming**: Use descriptive names that indicate project customization
5. **Testing**: Test project agents thoroughly before deployment
6. **Deployment**: Let the system auto-convert all formats to Markdown - don't manually edit `.claude/agents/*.md` files
7. **Maintenance**: Keep source agents updated with framework changes

## Migration Path

To migrate existing customizations to project agents:

1. Identify customized user agents specific to a project
2. Move them to project agents directory
3. Update any project-specific instructions
4. Test the migration with `test_project_agent_precedence.py`

## Agent Exclusion Configuration

Project agents can be excluded from deployment just like system agents. This is useful when you want to:
- Deploy only a subset of available project agents
- Test specific agent combinations
- Optimize deployment performance

### Configuration

Add exclusion configuration to `.claude-mpm/configuration.yaml`:

```yaml
agent_deployment:
  excluded_agents:
    - custom_agent_name      # Exclude specific project agent
    - another_project_agent  # Multiple exclusions
  case_sensitive: false      # Case-insensitive matching (default)
```

### Examples

**Exclude experimental project agents**:
```yaml
agent_deployment:
  excluded_agents:
    - experimental_feature_agent
    - beta_integration_agent
```

**Deploy only core project agents**:
```yaml
agent_deployment:
  excluded_agents:
    - payment_processor     # Skip payment agent for testing
    - notification_service  # Skip notifications for dev
    - analytics_tracker    # Skip analytics for privacy
```

### CLI Usage

```bash
# Deploy with exclusions (skips excluded project agents)
./claude-mpm agents deploy

# Deploy all agents including excluded ones
./claude-mpm agents deploy --include-all

# Check which project agents are deployed
./claude-mpm agents list --by-tier
```

**Note**: Exclusions apply to both system and project agents. The same exclusion configuration affects all agent tiers.

See [Agent Exclusion Guide](AGENT_EXCLUSION.md) for comprehensive exclusion documentation.

## Available System Agents

Claude MPM includes several specialized system agents that can be customized at the project level:

### Core Agents
- **Engineer Agent**: Software development and implementation
- **QA Agent**: Testing, quality assurance, and validation  
- **Documentation Agent**: Technical writing and documentation management
- **Security Agent**: Security analysis and vulnerability management
- **Ops Agent**: Operations, deployment, and infrastructure management

### Specialized Agents
- **Data Engineer Agent**: Data pipeline and analytics work
- **Research Agent**: Investigation and analysis tasks
- **Version Control Agent**: Git and version management operations
- **Code Analyzer Agent**: Static code analysis and quality metrics
- **Deploy Manager Agent**: Release and deployment coordination
- **Ticketing Agent**: Project management and issue tracking

### Project Management
- **Ticketing Agent**: Intelligent ticket management for epics, issues, and tasks with workflow automation. See [Ticketing Agent Documentation](TICKETING_AGENT.md) for comprehensive usage guide.

Each system agent can be customized or overridden at the project level by creating agent definitions in `.claude-mpm/agents/` with the same agent ID.

## Troubleshooting

### Agent Not Found
- Verify file is in `.claude-mpm/agents/` directory
- Check file extension is supported (`.json`, `.yaml`, `.yml`, or `.md`)
- Ensure file name follows naming conventions
- Run deployment if needed to generate `.claude/agents/*.md` files
- **Check exclusions**: Verify agent isn't excluded in `agent_deployment.excluded_agents`

### Wrong Agent Version Loaded
- Check tier precedence with `registry.get_agent(name).tier`
- Use `force_refresh=True` to bypass cache
- Verify no naming conflicts
- **Check exclusions**: Ensure desired agent isn't excluded from deployment

### Agent Seems Missing After Deployment
- **Check exclusion configuration**: Agent may be excluded via `agent_deployment.excluded_agents`
- **Use `--include-all`**: Try deploying with `./claude-mpm agents deploy --include-all`
- **Case sensitivity**: Check if agent name case matches configuration (when `case_sensitive: true`)

### Cache Issues
- Force refresh: `registry.discover_agents(force_refresh=True)`
- Clear cache: `registry.invalidate_cache()`
- Check file permissions on agent files