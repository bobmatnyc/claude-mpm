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