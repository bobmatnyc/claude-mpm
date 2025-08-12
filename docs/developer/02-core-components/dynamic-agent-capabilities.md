# Dynamic Agent Capabilities System

The dynamic agent capabilities system automatically generates agent documentation from deployed agents, ensuring that the framework's INSTRUCTIONS.md always reflects the actual available agents rather than static, potentially outdated descriptions.

## Overview

The system replaces the static `{{capabilities-list}}` placeholder in INSTRUCTIONS.md with dynamically generated content that discovers and documents all deployed agents in real-time.

## Architecture

### Core Components

1. **DeployedAgentDiscovery** (`services/deployed_agent_discovery.py`)
   - Discovers all deployed agents using the AgentRegistry
   - Extracts agent metadata, capabilities, and tools
   - Handles both new standardized schema and legacy formats
   - Respects project > user > system precedence

2. **AgentCapabilitiesGenerator** (`services/agent_capabilities_generator.py`)
   - Generates markdown documentation from discovered agents
   - Groups agents by source tier (project, user, system)
   - Creates formatted lists of capabilities and specializations
   - Uses Jinja2 templates for consistent formatting

3. **ContentAssembler** (`framework_claude_md_generator/content_assembler.py`)
   - Enhanced to support template variable substitution
   - Integrates with discovery and generation services
   - Applies dynamic content during assembly

4. **DeploymentManager** (`framework_claude_md_generator/deployment_manager.py`)
   - Triggers fresh capability generation on deployment
   - Ensures deployed INSTRUCTIONS.md contains current agent data
   - Handles placeholder detection and content processing

## How It Works

### Discovery Process

1. **Agent Detection**: The system queries the AgentRegistry for all available agents
2. **Metadata Extraction**: For each agent, it extracts:
   - ID and name
   - Description and specializations
   - Capabilities and tools
   - Source tier (project/user/system)

3. **Format Handling**: Supports both:
   - New standardized schema (v2.0.0+)
   - Legacy agent formats for backward compatibility

### Capabilities Source of Truth

**Important**: Agent capabilities are discovered from deployed agents in `.claude/agents/` directory, not from source definitions in `.claude-mpm/agents/`. This ensures consistency with what Claude Code actually has access to.

#### Discovery Order and Precedence

The `SimpleAgentRegistry` implements the three-tier precedence system:

1. **PROJECT Tier**: `.claude/agents/` agents deployed from `.claude-mpm/agents/`
2. **USER Tier**: `.claude/agents/` agents deployed from `~/.claude-mpm/agents/`
3. **SYSTEM Tier**: `.claude/agents/` built-in framework agents

#### Technical Implementation

```python
# DeployedAgentDiscovery queries the deployed agents
def discover_agents(self):
    agents = self.registry.list_agents()  # Gets from .claude/agents/
    for agent in agents:
        metadata = self.registry.get_agent_metadata(agent.id)  # From deployed files
        capabilities = self._extract_capabilities(metadata)
```

**Key Points**:
- **Deployed Only**: Only agents in `.claude/agents/` appear in capabilities
- **Real-time Reflection**: Shows capabilities of currently deployed versions
- **Consistency Guarantee**: Capabilities match what Claude Code uses
- **Deployment Requirement**: Project agents must be deployed to be discoverable

#### Example: Deployment Impact on Capabilities

```bash
# 1. Create project agent with capabilities
echo '{"capabilities": {"tools": ["custom_tool"]}}' > .claude-mpm/agents/test.json

# 2. Capabilities NOT discoverable yet
./claude-mpm agents list --deployed  # test agent missing

# 3. Deploy to make discoverable
./claude-mpm agents deploy

# 4. NOW discoverable in capabilities
./claude-mpm agents list --deployed  # test agent appears with tools
```

### Content Generation

The generated content includes:

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

### Integration Flow

```
INSTRUCTIONS.md Template
    ↓
{{capabilities-list}} placeholder detected
    ↓
DeploymentManager triggers processing
    ↓
ContentAssembler calls DeployedAgentDiscovery
    ↓
AgentCapabilitiesGenerator creates content
    ↓
Template substitution applied
    ↓
Final INSTRUCTIONS.md deployed
```

## Implementation Details

### Code References

The capabilities discovery system relies on several key components:

#### SimpleAgentRegistry (`src/claude_mpm/services/agents/registry.py`)

The registry provides the foundation for agent discovery:

```python
class SimpleAgentRegistry:
    def list_agents(self) -> List[AgentInfo]:
        """Lists agents from .claude/agents/ following precedence rules"""
        
    def get_agent_metadata(self, agent_id: str) -> Dict:
        """Gets metadata from deployed agent files"""
        
    def discover_agents(self, force_refresh: bool = False) -> Dict:
        """Discovers agents with three-tier precedence"""
```

#### DeployedAgentDiscovery (`src/claude_mpm/services/deployed_agent_discovery.py`)

Wraps the registry to provide capability-focused discovery:

```python
class DeployedAgentDiscovery:
    def __init__(self):
        self.registry = SimpleAgentRegistry()
        
    def discover_agents(self) -> List[Dict]:
        """Discovers deployed agents and extracts capabilities"""
        agents = self.registry.list_agents()
        return [self._process_agent(agent) for agent in agents]
```

#### File System Organization

The discovery system reads from the standardized directory structure:

```
project/
├── .claude-mpm/agents/          # Source agents (JSON only)
│   ├── custom_engineer.json     # Project-specific source
│   └── domain_expert.json       # Project-specific source
├── .claude/agents/              # Deployed agents (Markdown)
│   ├── custom_engineer.md       # ← Capabilities read from here
│   ├── domain_expert.md         # ← Capabilities read from here
│   ├── engineer.md              # System agent (deployed)
│   └── qa.md                    # System agent (deployed)
```

**Discovery Flow**:
1. Scan `.claude/agents/` for deployed agents
2. Parse frontmatter from Markdown files
3. Extract capabilities, tools, model preferences
4. Apply precedence rules (project > user > system)
5. Return consolidated capabilities list

### Error Handling

- **Graceful Fallback**: If discovery fails, the placeholder remains unchanged
- **Empty Agent List**: Generates minimal valid content with "0 deployed agents" note
- **Invalid Formats**: Filters out template agents and invalid entries

### Performance

- **Discovery Time**: ~0.6ms for agent discovery
- **Generation Time**: ~1.1ms for content generation
- **Total Overhead**: ~3.3ms (well under 200ms requirement)
- **Caching**: Optional 5-minute cache for production environments

### Template Variables

The system supports template variable substitution using Jinja2:

```python
# In ContentAssembler
template_variables['capabilities-list'] = capabilities_content
template = Template(full_content)
return template.render(**template_variables)
```

## Usage

### For Framework Developers

1. **Adding Template Variables**: Edit INSTRUCTIONS.md template to include `{{variable-name}}`
2. **Extending Generation**: Add new methods to AgentCapabilitiesGenerator
3. **Custom Formatting**: Modify the Jinja2 template in the generator

### For Agent Developers

The system automatically picks up any properly deployed agents:
- Place agents in appropriate directories
- Follow the standardized agent schema
- The documentation updates automatically on deployment

## Benefits

1. **Always Current**: Documentation reflects actual deployed agents
2. **Zero Maintenance**: No manual updates needed
3. **Project Awareness**: Shows project-specific agent customizations
4. **Backward Compatible**: Works with existing agent formats
5. **Performance**: Minimal overhead (<5ms total)

## Testing

Run the test suite for dynamic capabilities:

```bash
# Unit tests
pytest tests/test_deployed_agent_discovery.py
pytest tests/test_agent_capabilities_generator.py

# Integration test
python scripts/test_dynamic_capabilities.py
```

## Future Enhancements

- **Rich Capabilities**: Extract more detailed capability information
- **Tool Documentation**: Auto-generate tool usage examples
- **Version Tracking**: Show agent version information
- **Dependency Graphs**: Visualize agent relationships