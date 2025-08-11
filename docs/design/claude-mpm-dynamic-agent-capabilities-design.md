# Claude MPM Dynamic Agent Capabilities Design

**Document Version:** 1.0  
**Date:** July 27, 2025  
**Status:** Implementation Ready  
**Scope:** Replace static agent descriptions with dynamic content from deployed agents

## Overview

Replace hardcoded agent capabilities in INSTRUCTIONS.md with dynamically generated content from actual deployed agents. This ensures the framework instructions always reflect the real, available agents rather than outdated static descriptions.

## Two-Phase Implementation

### Phase 1: Agent Discovery and Content Generation
**Goal:** Generate agent capability descriptions from deployed agents in the project

### Phase 2: Template Substitution and Integration  
**Goal:** Replace `{{ capabilities-list }}` placeholder in INSTRUCTIONS.md with generated content

## Current State Analysis

### Static Content Location
```markdown
# Current INSTRUCTIONS.md contains hardcoded sections like:
## Agent Names & Capabilities
**Core Agents**: research, engineer, qa, documentation, security, ops, version_control, data_engineer

**Agent Capabilities**:
- **Research**: Codebase analysis, best practices, technical investigation
- **Engineer**: Implementation, refactoring, debugging
# ... etc (hardcoded and potentially outdated)
```

### Problem Statement
- Agent capabilities become stale when agents are updated
- No reflection of project-specific agent customizations
- Manual maintenance required for accuracy
- Deployed agents may differ from documentation

## Phase 1: Agent Discovery and Content Generation

### 1.1 Deployed Agent Discovery Service

```python
# File: src/claude_mpm/services/deployed_agent_discovery.py

from pathlib import Path
from typing import List, Dict, Any
from claude_mpm.core.agent_registry import AgentRegistryAdapter
from claude_mpm.utils.paths import PathResolver

class DeployedAgentDiscovery:
    """Discovers and analyzes deployed agents in the project."""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or PathResolver.get_project_root()
        self.agent_registry = AgentRegistryAdapter()
    
    def discover_deployed_agents(self) -> List[Dict[str, Any]]:
        """Discover all deployed agents following hierarchy precedence."""
        
        # Get effective agents (respects project > user > system precedence)
        agents = self.agent_registry.list_agents()
        
        deployed_agents = []
        for agent in agents:
            agent_info = self._extract_agent_info(agent)
            if agent_info:
                deployed_agents.append(agent_info)
        
        return deployed_agents
    
    def _extract_agent_info(self, agent) -> Dict[str, Any]:
        """Extract relevant information from agent definition."""
        
        # Handle both new schema (agent.metadata) and legacy formats
        if hasattr(agent, 'metadata'):
            # New standardized schema
            return {
                'id': agent.agent_id,
                'name': agent.metadata.name,
                'description': agent.metadata.description,
                'specializations': agent.metadata.specializations,
                'capabilities': getattr(agent, 'capabilities', {}),
                'source_tier': self._determine_source_tier(agent),
                'tools': getattr(agent.configuration, 'tools', []) if hasattr(agent, 'configuration') else []
            }
        else:
            # Legacy format fallback
            return {
                'id': getattr(agent, 'agent_id', getattr(agent, 'type', 'unknown')),
                'name': getattr(agent, 'name', agent.type.title() if hasattr(agent, 'type') else 'Unknown'),
                'description': getattr(agent, 'description', 'No description available'),
                'specializations': getattr(agent, 'specializations', []),
                'capabilities': {},
                'source_tier': self._determine_source_tier(agent),
                'tools': getattr(agent, 'tools', [])
            }
    
    def _determine_source_tier(self, agent) -> str:
        """Determine if agent comes from project, user, or system tier."""
        # Implementation depends on how agent registry tracks source
        # Could check file paths or agent metadata
        return getattr(agent, 'source_tier', 'system')
```

### 1.2 Agent Capabilities Content Generator

```python
# File: src/claude_mpm/services/agent_capabilities_generator.py

from typing import List, Dict, Any
from jinja2 import Template

class AgentCapabilitiesGenerator:
    """Generates markdown content for agent capabilities section."""
    
    def __init__(self):
        self.template = self._load_template()
    
    def generate_capabilities_section(self, deployed_agents: List[Dict[str, Any]]) -> str:
        """Generate the complete agent capabilities markdown section."""
        
        # Group agents by source tier for organized display
        agents_by_tier = self._group_by_tier(deployed_agents)
        
        # Generate core agent list
        core_agent_list = self._generate_core_agent_list(deployed_agents)
        
        # Generate detailed capabilities
        detailed_capabilities = self._generate_detailed_capabilities(deployed_agents)
        
        # Render template
        return self.template.render(
            core_agents=core_agent_list,
            detailed_capabilities=detailed_capabilities,
            agents_by_tier=agents_by_tier,
            total_agents=len(deployed_agents)
        )
    
    def _group_by_tier(self, agents: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group agents by their source tier."""
        tiers = {'system': [], 'user': [], 'project': []}
        
        for agent in agents:
            tier = agent.get('source_tier', 'system')
            if tier in tiers:
                tiers[tier].append(agent)
        
        return tiers
    
    def _generate_core_agent_list(self, agents: List[Dict[str, Any]]) -> str:
        """Generate comma-separated list of core agent IDs."""
        agent_ids = [agent['id'] for agent in agents]
        return ', '.join(sorted(agent_ids))
    
    def _generate_detailed_capabilities(self, agents: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Generate detailed capability descriptions for each agent."""
        capabilities = []
        
        for agent in sorted(agents, key=lambda a: a['id']):
            # Extract key capabilities
            specializations = agent.get('specializations', [])
            when_to_use = agent.get('capabilities', {}).get('when_to_use', [])
            
            # Create capability summary
            if when_to_use:
                capability_text = '; '.join(when_to_use[:2])  # First 2 items
            elif specializations:
                capability_text = ', '.join(specializations[:3])  # First 3 specializations
            else:
                capability_text = agent.get('description', 'General purpose agent')
            
            capabilities.append({
                'name': agent['name'],
                'id': agent['id'],
                'capability_text': capability_text,
                'tools': ', '.join(agent.get('tools', [])[:5])  # First 5 tools
            })
        
        return capabilities
    
    def _load_template(self) -> Template:
        """Load the Jinja2 template for agent capabilities."""
        template_content = """
## Agent Names & Capabilities
**Core Agents**: {{ core_agents }}

{% if agents_by_tier.project %}
### Project-Specific Agents
{% for agent in agents_by_tier.project %}
- **{{ agent.name }}** ({{ agent.id }}): {{ agent.description }}
{% endfor %}

{% endif %}
**Agent Capabilities**:
{% for cap in detailed_capabilities %}
- **{{ cap.name }}**: {{ cap.capability_text }}
{% endfor %}

**Agent Name Formats** (both valid):
- Capitalized: {{ detailed_capabilities | map(attribute='name') | join('", "') }}
- Lowercase-hyphenated: {{ detailed_capabilities | map(attribute='id') | join('", "') }}

*Generated from {{ total_agents }} deployed agents*
""".strip()
        
        return Template(template_content)
```

## Phase 2: Template Substitution and Integration

### 2.1 Enhanced Framework Generator Integration

```python
# File: src/claude_mpm/framework_claude_md_generator/content_assembler.py
# (Enhancement to existing ContentAssembler)

from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery
from claude_mpm.services.agents.management import AgentCapabilitiesGenerator
from jinja2 import Template

class ContentAssembler:
    """Enhanced to support dynamic agent capabilities generation."""
    
    def __init__(self):
        self.agent_discovery = DeployedAgentDiscovery()
        self.capabilities_generator = AgentCapabilitiesGenerator()
    
    def assemble_content(self, sections: List[str], template_variables: Dict[str, str]) -> str:
        """Assemble content with dynamic agent capabilities substitution."""
        
        # Generate dynamic capabilities content
        deployed_agents = self.agent_discovery.discover_deployed_agents()
        capabilities_content = self.capabilities_generator.generate_capabilities_section(deployed_agents)
        
        # Add to template variables
        template_variables['capabilities-list'] = capabilities_content
        
        # Combine all sections
        full_content = '\n'.join(sections)
        
        # Apply template substitution
        template = Template(full_content)
        return template.render(**template_variables)
```

### 2.2 INSTRUCTIONS.md Template Update

```markdown
# File: framework/INSTRUCTIONS.md (template)

# Claude Multi-Agent Project Manager Instructions
<!-- FRAMEWORK_VERSION: {{ framework_version }} -->

## Core Identity & Authority
<!-- ... existing content ... -->

{{ capabilities-list }}

## Enhanced Task Delegation Format
<!-- ... rest of existing content ... -->
```

### 2.3 Deployment Manager Enhancement

```python
# File: src/claude_mpm/framework_claude_md_generator/deployment_manager.py
# (Enhancement to ensure capabilities are regenerated on each deployment)

class DeploymentManager:
    def deploy_to_parent(self, content: str, parent_path: Path, force: bool = False) -> bool:
        """Deploy with fresh agent capabilities generation."""
        
        # Force regeneration of agent capabilities before deployment
        # This ensures the most current deployed agents are reflected
        
        # Check if content contains template variables that need processing
        if '{{ capabilities-list }}' in content:
            # Content needs processing - let ContentAssembler handle it
            from .content_assembler import ContentAssembler
            assembler = ContentAssembler()
            
            # Re-process content to get fresh agent data
            processed_content = assembler.assemble_content([content], {})
            content = processed_content
        
        # Continue with normal deployment
        return self._write_content_to_file(content, parent_path, force)
```

## Implementation Steps

### Step 1: Create Agent Discovery Service
1. Create `DeployedAgentDiscovery` class
2. Integrate with existing `AgentRegistryAdapter`
3. Test agent discovery with current project structure
4. Verify precedence rules work correctly

### Step 2: Create Content Generator
1. Create `AgentCapabilitiesGenerator` class
2. Design and test Jinja2 template
3. Test with sample agent data
4. Verify markdown output quality

### Step 3: Integrate with Framework Generator
1. Enhance `ContentAssembler` class
2. Add template variable support
3. Test with existing framework generation flow
4. Verify backward compatibility

### Step 4: Update Template and Deploy
1. Add `{{ capabilities-list }}` to INSTRUCTIONS.md template
2. Update deployment process
3. Test end-to-end generation
4. Verify Claude Code can load generated instructions

## Testing Strategy

### Unit Tests
```python
def test_agent_discovery():
    """Test deployed agent discovery."""
    discovery = DeployedAgentDiscovery()
    agents = discovery.discover_deployed_agents()
    
    assert len(agents) > 0
    assert all('id' in agent for agent in agents)
    assert all('name' in agent for agent in agents)

def test_capabilities_generation():
    """Test capabilities content generation."""
    generator = AgentCapabilitiesGenerator()
    
    sample_agents = [
        {'id': 'research', 'name': 'Research Agent', 'description': 'Test', 'specializations': ['analysis']},
        {'id': 'engineer', 'name': 'Engineer Agent', 'description': 'Test', 'specializations': ['coding']}
    ]
    
    content = generator.generate_capabilities_section(sample_agents)
    
    assert 'research, engineer' in content
    assert 'Research Agent' in content
    assert 'Engineer Agent' in content
```

### Integration Tests
```python
def test_end_to_end_generation():
    """Test complete flow from discovery to deployment."""
    # Deploy test agents
    # Generate INSTRUCTIONS.md
    # Verify content contains deployed agent info
    # Verify no hardcoded agent references remain
```

## Risk Mitigation

### Error Handling
- **Agent discovery failure**: Fall back to static content with warning
- **Template rendering failure**: Log error and use fallback template
- **Empty agent list**: Generate minimal template with explanation

### Performance Considerations
- **Caching**: Cache discovered agents for 5-10 minutes to avoid repeated file I/O
- **Lazy loading**: Only discover agents when generating content
- **Minimal processing**: Keep agent analysis lightweight

### Backward Compatibility
- **Template fallback**: Support both `{{ capabilities-list }}` and static content
- **Legacy agent format**: Handle both new standardized schema and legacy formats
- **Graceful degradation**: System works even if dynamic generation fails

## Success Criteria

1. **Accuracy**: Generated content reflects actual deployed agents
2. **Completeness**: All deployed agents appear in capabilities list
3. **Precedence**: Project agents override system agents in documentation
4. **Performance**: Generation adds <200ms to framework generation time
5. **Reliability**: Fallback ensures system continues working if generation fails

This focused design addresses exactly your requirement: replace static agent descriptions with dynamic content from deployed agents in a clean two-phase approach.