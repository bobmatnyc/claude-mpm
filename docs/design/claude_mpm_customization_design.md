# Claude MPM Agent and Workflow Customization Design

**Document Version:** 1.0  
**Date:** July 27, 2025  
**Status:** Design Phase  
**Scope:** Enable users to create, manage, and customize agents and workflows

## Important Implementation Notes

**⚠️ All Code Examples Are Suggestions Only**  
All code examples in this document are conceptual suggestions and must be adapted to match the existing Claude MPM codebase structure, patterns, and conventions. Implementation should follow established architecture, naming conventions, and integration patterns found in the current codebase.

**🎯 User-Driven Prompt-Based Configuration**  
All agent and workflow creation is driven by user prompts to Claude Code's PM. Users describe what they want, and the PM uses Claude MPM's internal API to build the configuration. The PM can validate results by starting a new interactive session and viewing the startup sequence.

## Architecture Overview

### User Interaction Flow

```
User Prompt to Claude Code PM
    ↓
"Create an agent that does X"
"Build workflow based on document Y"
    ↓
Claude Code PM analyzes requirements
    ↓
PM calls Claude MPM Internal API
    ↓
Claude MPM builds/modifies configuration
    ↓
PM starts new claude-mpm session
    ↓
User sees startup sequence with new config
    ↓
Validation complete - agent/workflow ready
```

### Internal API Architecture

Claude MPM exposes an internal API that Claude Code's PM can call to:
- Create/modify agents from requirements
- Build custom workflows from descriptions
- Generate instruction templates
- Manage agent availability
- Rebuild configurations

The PM validates results by launching a new claude-mpm interactive session and observing the startup sequence, which displays the active configuration.

## Current Architecture Analysis

### Existing Agent System
Based on the codebase analysis, Claude MPM currently uses:

- **Standardized JSON schema** for agent definitions (from Agent Schema Standardization doc)
- **Three-tier hierarchy**: Project → User → System precedence
- **Dynamic agent discovery** via `AgentRegistryAdapter`
- **Template-based instructions** with JINJA support in framework generator
- **Agent validation** through schema compliance

### Current Instruction System
- **Static INSTRUCTIONS.md** with template variables
- **Framework generator** that assembles content from sections
- **Dynamic capabilities** generated from deployed agents
- **Template substitution** using JINJA for variable replacement

## Feature Requirements

### A. Prompt-Driven Agent Creation

**User Experience:**
```
User: "Create an agent specialized in API testing that knows REST, GraphQL, and pytest"

PM: I'll create an API testing agent for you.
    [Calls Claude MPM API]
    Starting new session to validate...
    
    → New claude-mpm session starts
    → Startup shows: "Loading custom agent: api_testing_agent"
    → Agent available in workflow

User: ✅ Perfect! The agent is ready to use.
```

**Alternative with Document Reference:**
```
User: "Create an agent based on the requirements in ./docs/agent-spec.md"

PM: Analyzing the specification document...
    [Reads document, extracts requirements]
    [Calls Claude MPM API with extracted requirements]
    Starting new session to validate...
    
    → New claude-mpm session shows custom agent loaded
```

### B. Prompt-Driven Workflow Creation

**User Experience:**
```
User: "Create a workflow where we always do research first, then get approval, then implement"

PM: I'll create a custom workflow with approval gates.
    [Calls Claude MPM API]
    Starting new session to test...
    
    → New claude-mpm session starts
    → Startup shows: "Using custom workflow: approval-based-development"
    → PM behavior follows new workflow

User: ✅ Great! The workflow is active.
```

### C. Self-Validating Configuration

**Key Principle:** The PM can validate its own work by starting a fresh claude-mpm session and observing:
- Startup messages showing loaded agents
- Configuration display during initialization  
- Active workflow behavior
- Agent availability confirmation

## Detailed Design

### 1. Custom Agent Creation System

#### 1.1 Agent Creation Service

```python
# File: src/claude_mpm/services/agent_creation_service.py

from pathlib import Path
from typing import Dict, Any, Optional
import json
from datetime import datetime
from claude_mpm.core import LoggerMixin
from claude_mpm.utils.paths import PathResolver
from claude_mpm.services.agent_schema_validator import AgentSchemaValidator

class AgentCreationService(LoggerMixin):
    """Service for creating and managing custom agents."""
    
    def __init__(self):
        super().__init__()
        self.validator = AgentSchemaValidator()
        self.project_root = PathResolver.get_project_root()
        
    def create_agent_from_prompt(
        self, 
        prompt: str, 
        scope: str = "project",
        base_agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new agent from natural language prompt."""
        
        # Parse prompt to extract agent requirements
        agent_requirements = self._parse_agent_prompt(prompt)
        
        # Generate agent definition
        agent_definition = self._generate_agent_definition(
            agent_requirements, 
            base_agent_type
        )
        
        # Validate against schema
        validation_result = self.validator.validate_agent(agent_definition)
        if not validation_result.valid:
            raise ValueError(f"Generated agent failed validation: {validation_result.errors}")
        
        # Save agent
        agent_path = self._save_agent(agent_definition, scope)
        
        # Update agent index
        self._update_agent_index(agent_definition['agent_id'], scope)
        
        return {
            "agent_id": agent_definition['agent_id'],
            "agent_path": str(agent_path),
            "validation_warnings": validation_result.warnings
        }
    
    def _parse_agent_prompt(self, prompt: str) -> Dict[str, Any]:
        """Parse natural language prompt to extract agent requirements."""
        # Use Claude API to analyze prompt and extract:
        # - Agent purpose and capabilities
        # - Specialized knowledge areas
        # - Tool requirements
        # - Resource requirements
        # - When to use criteria
        
        analysis_prompt = f"""
        Analyze this agent creation request and extract structured information:
        
        "{prompt}"
        
        Return JSON with:
        - agent_id: snake_case identifier
        - name: human readable name
        - description: clear description (20-200 chars)
        - specializations: array of specialization areas
        - when_to_use: array of criteria for when to use this agent
        - specialized_knowledge: array of knowledge domains
        - unique_capabilities: array of unique value propositions
        - required_tools: array of tool names needed
        - resource_tier: lightweight|standard|intensive
        - base_agent_type: closest existing agent type or null
        """
        
        # Implementation would use Claude API or subprocess call
        # For now, return structured extraction
        return self._extract_from_prompt_analysis(prompt)
    
    def _generate_agent_definition(
        self, 
        requirements: Dict[str, Any],
        base_agent_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate complete agent definition from requirements."""
        
        # Start with standardized schema template
        agent_definition = {
            "schema_version": "1.0.0",
            "agent_id": requirements['agent_id'],
            "agent_version": "1.0.0",
            "agent_type": requirements.get('base_agent_type', 'custom'),
            "metadata": {
                "name": requirements['name'],
                "description": requirements['description'],
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "tags": requirements.get('tags', ['custom']),
                "specializations": requirements['specializations']
            },
            "capabilities": {
                "when_to_use": requirements['when_to_use'],
                "specialized_knowledge": requirements['specialized_knowledge'], 
                "unique_capabilities": requirements['unique_capabilities']
            },
            "configuration": self._generate_configuration(requirements),
            "instructions": self._generate_instructions(requirements)
        }
        
        return agent_definition
    
    def _save_agent(self, agent_definition: Dict[str, Any], scope: str) -> Path:
        """Save agent definition to appropriate location."""
        
        if scope == "project":
            agents_dir = self.project_root / ".claude-mpm" / "agents" / "custom"
        elif scope == "user":
            agents_dir = Path.home() / ".claude-mpm" / "agents" / "user"
        else:
            raise ValueError(f"Invalid scope: {scope}")
        
        agents_dir.mkdir(parents=True, exist_ok=True)
        
        agent_file = agents_dir / f"{agent_definition['agent_id']}.json"
        
        # Handle versioning if agent already exists
        if agent_file.exists():
            agent_definition = self._increment_version(agent_file, agent_definition)
        
        with open(agent_file, 'w') as f:
            json.dump(agent_definition, f, indent=2)
        
        self.logger.info(f"Saved agent {agent_definition['agent_id']} to {agent_file}")
        return agent_file
```

#### 1.2 Agent Modification Service

```python
# File: src/claude_mpm/services/agent_modification_service.py

class AgentModificationService(LoggerMixin):
    """Service for modifying existing agents with automatic versioning."""
    
    def modify_agent(
        self, 
        agent_id: str, 
        modification_prompt: str,
        scope: str = None
    ) -> Dict[str, Any]:
        """Modify an existing agent based on natural language prompt."""
        
        # Find existing agent
        current_agent = self._find_agent(agent_id, scope)
        if not current_agent:
            raise ValueError(f"Agent {agent_id} not found")
        
        # Parse modification requirements
        modifications = self._parse_modification_prompt(modification_prompt, current_agent)
        
        # Apply modifications
        modified_agent = self._apply_modifications(current_agent, modifications)
        
        # Increment version
        modified_agent = self._increment_semantic_version(modified_agent, modifications)
        
        # Validate
        validation_result = self.validator.validate_agent(modified_agent)
        if not validation_result.valid:
            raise ValueError(f"Modified agent failed validation: {validation_result.errors}")
        
        # Save with backup
        self._backup_current_version(current_agent)
        agent_path = self._save_modified_agent(modified_agent, scope)
        
        return {
            "agent_id": agent_id,
            "previous_version": current_agent['agent_version'],
            "new_version": modified_agent['agent_version'],
            "agent_path": str(agent_path),
            "changes_applied": modifications.get('changes_summary', [])
        }
    
    def _increment_semantic_version(self, agent: Dict[str, Any], modifications: Dict) -> Dict[str, Any]:
        """Increment version based on type of changes."""
        current_version = agent['agent_version']
        major, minor, patch = map(int, current_version.split('.'))
        
        change_type = modifications.get('change_type', 'patch')
        
        if change_type == 'major':  # Breaking changes to capabilities or interface
            major += 1
            minor = 0
            patch = 0
        elif change_type == 'minor':  # New capabilities or significant improvements
            minor += 1
            patch = 0
        else:  # Bug fixes or minor tweaks
            patch += 1
        
        agent['agent_version'] = f"{major}.{minor}.{patch}"
        agent['metadata']['updated_at'] = datetime.now().isoformat()
        
        return agent
```

### 2. Agent Availability Management

#### 2.1 Agent Index System

```python
# File: src/claude_mpm/services/agent_index_service.py

class AgentIndexService(LoggerMixin):
    """Manages agent availability and indexing for fast startup."""
    
    def __init__(self):
        super().__init__()
        self.project_root = PathResolver.get_project_root()
    
    def build_agent_index(self) -> Dict[str, Any]:
        """Build comprehensive agent index with precedence resolution."""
        
        index = {
            "version": "1.0.0",
            "built_at": datetime.now().isoformat(),
            "agents": {},
            "precedence_order": ["project", "user", "system"],
            "active_agents": []
        }
        
        # Discover agents in all tiers
        project_agents = self._discover_project_agents()
        user_agents = self._discover_user_agents()
        system_agents = self._discover_system_agents()
        
        # Resolve precedence and build final agent list
        all_agents = {
            "project": project_agents,
            "user": user_agents,
            "system": system_agents
        }
        
        resolved_agents = self._resolve_agent_precedence(all_agents)
        
        index["agents"] = resolved_agents
        index["active_agents"] = list(resolved_agents.keys())
        
        # Save index
        self._save_index(index)
        
        return index
    
    def _resolve_agent_precedence(self, all_agents: Dict) -> Dict[str, Dict]:
        """Resolve agent precedence following project → user → system hierarchy."""
        
        resolved = {}
        
        # Start with system agents as base
        for agent_id, agent_info in all_agents["system"].items():
            resolved[agent_id] = {
                **agent_info,
                "source_tier": "system",
                "overridden_by": None
            }
        
        # Override with user agents
        for agent_id, agent_info in all_agents["user"].items():
            if agent_id in resolved:
                resolved[agent_id]["overridden_by"] = "user"
            resolved[agent_id] = {
                **agent_info,
                "source_tier": "user", 
                "overrides": "system" if agent_id in all_agents["system"] else None
            }
        
        # Override with project agents (highest precedence)
        for agent_id, agent_info in all_agents["project"].items():
            previous_tier = resolved.get(agent_id, {}).get("source_tier")
            resolved[agent_id] = {
                **agent_info,
                "source_tier": "project",
                "overrides": previous_tier
            }
        
        return resolved
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent IDs."""
        index = self._load_index()
        return index.get("active_agents", [])
    
    def enable_agent(self, agent_id: str) -> bool:
        """Enable an agent in the current context."""
        index = self._load_index()
        
        if agent_id not in index["agents"]:
            raise ValueError(f"Agent {agent_id} not found")
        
        if agent_id not in index["active_agents"]:
            index["active_agents"].append(agent_id)
            self._save_index(index)
            self.logger.info(f"Enabled agent: {agent_id}")
            return True
        
        return False
    
    def disable_agent(self, agent_id: str) -> bool:
        """Disable an agent in the current context."""
        index = self._load_index()
        
        if agent_id in index["active_agents"]:
            index["active_agents"].remove(agent_id)
            self._save_index(index)
            self.logger.info(f"Disabled agent: {agent_id}")
            return True
        
        return False
```

### 3. Custom Instructions and Workflow System

#### 3.1 Modular Instructions Architecture

```yaml
# File: config/instruction_sections.yaml
# Defines the modular structure of INSTRUCTIONS.md

sections:
  core:
    - identity_and_authority
    - context_aware_selection
    - mandatory_workflow
    - task_delegation_format
    
  workflow:
    - research_first_protocol
    - error_handling_protocol
    - standard_operating_procedure
    
  agents:
    - agent_capabilities  # Dynamic content
    - agent_names_formats
    
  advanced:
    - todowrite_requirements
    - completion_summary_protocol
    - example_interactions
    - advanced_features

# Each section can be:
# - system: built-in framework sections
# - user: user-defined override at ~/.claude-mpm/instructions/
# - project: project-specific override at .claude-mpm/instructions/
```

#### 3.2 Custom Instructions Service

```python
# File: src/claude_mpm/services/custom_instructions_service.py

class CustomInstructionsService(LoggerMixin):
    """Manages custom instructions and workflow definitions."""
    
    def __init__(self):
        super().__init__()
        self.project_root = PathResolver.get_project_root()
        self.sections_config = self._load_sections_config()
    
    def create_custom_workflow(
        self, 
        workflow_prompt: str, 
        scope: str = "project",
        sections_to_customize: List[str] = None
    ) -> Dict[str, Any]:
        """Create custom workflow instructions from natural language."""
        
        # Parse workflow requirements
        workflow_requirements = self._parse_workflow_prompt(workflow_prompt)
        
        # Generate markdown sections
        custom_sections = {}
        for section in (sections_to_customize or ['workflow']):
            if section in self.sections_config['sections']:
                content = self._generate_section_content(section, workflow_requirements)
                custom_sections[section] = content
        
        # Save custom sections
        saved_files = self._save_custom_sections(custom_sections, scope)
        
        # Rebuild instructions
        self._rebuild_instructions()
        
        return {
            "sections_created": list(custom_sections.keys()),
            "files_saved": saved_files,
            "scope": scope
        }
    
    def _generate_section_content(self, section: str, requirements: Dict) -> str:
        """Generate markdown content for a specific section."""
        
        templates = {
            "workflow": self._generate_workflow_section,
            "identity_and_authority": self._generate_identity_section,
            "mandatory_workflow": self._generate_mandatory_workflow_section
        }
        
        generator = templates.get(section, self._generate_generic_section)
        return generator(requirements)
    
    def _generate_workflow_section(self, requirements: Dict) -> str:
        """Generate custom workflow section."""
        
        workflow_template = """
## Custom Workflow Protocol
{workflow_description}

### Workflow Steps
{workflow_steps}

### Quality Gates
{quality_gates}

### Escalation Procedures
{escalation_procedures}
""".strip()
        
        return workflow_template.format(
            workflow_description=requirements.get('description', ''),
            workflow_steps=self._format_workflow_steps(requirements.get('steps', [])),
            quality_gates=self._format_quality_gates(requirements.get('quality_gates', [])),
            escalation_procedures=requirements.get('escalation', 'Standard PM escalation applies.')
        )
    
    def rebuild_instructions(self) -> Path:
        """Rebuild complete INSTRUCTIONS.md with custom sections."""
        
        # Load all section sources (system, user, project)
        sections_content = {}
        
        for category, section_list in self.sections_config['sections'].items():
            for section in section_list:
                content = self._load_section_with_precedence(section)
                sections_content[section] = content
        
        # Generate dynamic content (agent capabilities)
        dynamic_content = self._generate_dynamic_content()
        sections_content.update(dynamic_content)
        
        # Assemble final instructions
        template_vars = {
            'framework_version': self._get_framework_version(),
            **sections_content
        }
        
        instructions_content = self._assemble_instructions(template_vars)
        
        # Save to project
        instructions_path = self.project_root / "INSTRUCTIONS.md"
        with open(instructions_path, 'w') as f:
            f.write(instructions_content)
        
        self.logger.info(f"Rebuilt instructions at {instructions_path}")
        return instructions_path
    
    def _load_section_with_precedence(self, section: str) -> str:
        """Load section content following project → user → system precedence."""
        
        # Check project level
        project_path = self.project_root / ".claude-mpm" / "instructions" / f"{section}.md"
        if project_path.exists():
            return project_path.read_text()
        
        # Check user level
        user_path = Path.home() / ".claude-mpm" / "instructions" / f"{section}.md"
        if user_path.exists():
            return user_path.read_text()
        
        # Fall back to system level
        system_path = PathResolver.get_framework_root() / "framework" / "instructions" / f"{section}.md"
        if system_path.exists():
            return system_path.read_text()
        
        self.logger.warning(f"Section {section} not found in any tier")
        return f"<!-- Section {section} not found -->"
```

### 4. CLI Integration

#### 4.1 Agent Management Commands

```python
# File: src/claude_mpm/cli/agent_commands.py

@click.group()
def agent():
    """Manage custom agents."""
    pass

@agent.command()
@click.argument('prompt')
@click.option('--scope', default='project', type=click.Choice(['project', 'user']))
@click.option('--base-type', help='Base agent type to extend')
def create(prompt, scope, base_type):
    """Create a new agent from description."""
    try:
        service = AgentCreationService()
        result = service.create_agent_from_prompt(prompt, scope, base_type)
        
        click.echo(f"✅ Created agent: {result['agent_id']}")
        click.echo(f"📁 Saved to: {result['agent_path']}")
        
        if result['validation_warnings']:
            click.echo("⚠️  Warnings:")
            for warning in result['validation_warnings']:
                click.echo(f"   {warning}")
                
    except Exception as e:
        click.echo(f"❌ Error creating agent: {e}")

@agent.command()
@click.argument('agent_id')
@click.argument('modification_prompt')
@click.option('--scope', help='Scope to search for agent')
def modify(agent_id, modification_prompt, scope):
    """Modify an existing agent."""
    try:
        service = AgentModificationService()
        result = service.modify_agent(agent_id, modification_prompt, scope)
        
        click.echo(f"✅ Modified agent: {agent_id}")
        click.echo(f"📈 Version: {result['previous_version']} → {result['new_version']}")
        
    except Exception as e:
        click.echo(f"❌ Error modifying agent: {e}")

@agent.command()
def list():
    """List available agents."""
    try:
        index_service = AgentIndexService()
        index = index_service.build_agent_index()
        
        click.echo("📋 Available Agents:")
        for agent_id, agent_info in index['agents'].items():
            active = "✅" if agent_id in index['active_agents'] else "⭕"
            source = agent_info['source_tier']
            click.echo(f"  {active} {agent_id} ({source})")
            
    except Exception as e:
        click.echo(f"❌ Error listing agents: {e}")

@agent.command()
@click.argument('agent_id')
def enable(agent_id):
    """Enable an agent."""
    try:
        service = AgentIndexService()
        if service.enable_agent(agent_id):
            click.echo(f"✅ Enabled agent: {agent_id}")
        else:
            click.echo(f"⚠️  Agent {agent_id} already enabled")
    except Exception as e:
        click.echo(f"❌ Error: {e}")

@agent.command()
@click.argument('agent_id')
def disable(agent_id):
    """Disable an agent."""
    try:
        service = AgentIndexService()
        if service.disable_agent(agent_id):
            click.echo(f"✅ Disabled agent: {agent_id}")
        else:
            click.echo(f"⚠️  Agent {agent_id} not currently enabled")
    except Exception as e:
        click.echo(f"❌ Error: {e}")
```

#### 4.2 Workflow Management Commands

```python
# File: src/claude_mpm/cli/workflow_commands.py

@click.group()
def workflow():
    """Manage custom workflows and instructions."""
    pass

@workflow.command()
@click.argument('workflow_prompt')
@click.option('--scope', default='project', type=click.Choice(['project', 'user']))
@click.option('--sections', help='Comma-separated list of sections to customize')
def create(workflow_prompt, scope, sections):
    """Create custom workflow from description."""
    try:
        service = CustomInstructionsService()
        sections_list = sections.split(',') if sections else None
        
        result = service.create_custom_workflow(workflow_prompt, scope, sections_list)
        
        click.echo(f"✅ Created custom workflow ({scope})")
        click.echo(f"📝 Sections: {', '.join(result['sections_created'])}")
        click.echo(f"📁 Files: {len(result['files_saved'])}")
        
    except Exception as e:
        click.echo(f"❌ Error creating workflow: {e}")

@workflow.command()
def rebuild():
    """Rebuild INSTRUCTIONS.md with current customizations."""
    try:
        service = CustomInstructionsService()
        instructions_path = service.rebuild_instructions()
        
        click.echo(f"✅ Rebuilt instructions at {instructions_path}")
        
    except Exception as e:
        click.echo(f"❌ Error rebuilding instructions: {e}")

@workflow.command()
def status():
    """Show current workflow customizations."""
    try:
        service = CustomInstructionsService()
        status = service.get_customization_status()
        
        click.echo("📋 Workflow Customization Status:")
        for tier in ['project', 'user', 'system']:
            if status[tier]:
                click.echo(f"  {tier.title()}:")
                for section in status[tier]:
                    click.echo(f"    ✅ {section}")
                    
    except Exception as e:
        click.echo(f"❌ Error getting status: {e}")
```

## Implementation Plan

### Phase 1: Internal API Foundation (Week 1)
1. **Build Configuration API** - Core service for agent/workflow creation
2. **Requirements Parser** - Extract structured requirements from prompts
3. **Document Analyzer** - Parse specification documents for requirements
4. **Basic Validation** - Schema validation and configuration integrity

**⚠️ All implementations must follow existing codebase patterns and integrate with current services**

### Phase 2: PM Integration (Week 2)
1. **PM Interface Layer** - Clean API for Claude Code PM to call
2. **Session Management** - Start/monitor validation sessions
3. **Startup Preview** - Generate configuration previews
4. **PM Instructions Update** - Add agent/workflow creation authority to INSTRUCTIONS.md

### Phase 3: Validation & Testing (Week 3)
1. **Startup Sequence Monitoring** - Parse and validate configuration loading
2. **End-to-End Testing** - Full PM → API → Validation flow
3. **Error Handling** - Robust error reporting and recovery
4. **Documentation** - User guides and PM behavior examples

### Phase 4: CLI Integration & Polish (Week 4)
1. **CLI Commands** - Backup access to API functionality
2. **Configuration Management** - Advanced agent/workflow management
3. **Performance Optimization** - Fast startup with custom configurations
4. **User Experience** - Smooth workflow and clear feedback

## Success Criteria

1. **Natural Language Creation**: PM can create agents from user descriptions
2. **Document-Based Creation**: PM can build agents from specification files
3. **Self-Validation**: PM validates results by starting new claude-mpm sessions
4. **Startup Visibility**: Users see custom configurations in startup sequence
5. **Workflow Integration**: Custom agents/workflows work seamlessly in sessions
6. **Performance**: No significant startup time impact from customizations

## Key Design Principles

### Prompt-Driven Everything
- All customization starts with user prompts to Claude Code PM
- PM analyzes requirements and calls Claude MPM internal API
- No complex CLI workflows required for basic usage

### Self-Validating
- PM tests its own work by starting fresh claude-mpm sessions
- Startup sequence shows configuration status
- Users validate simply by observing session behavior

### API-First Architecture
- Clean internal API that PM calls
- CLI provides backup access to same functionality
- All configuration logic centralized in API layer

### Transparent Operation
- Startup sequence clearly shows custom configurations
- Users can see which agents/workflows are active
- Configuration changes immediately visible in new sessions

## Usage Examples

### Example 1: Creating a Custom Agent

**User:** "Create an agent that specializes in API testing and knows about REST, GraphQL, and pytest"

**PM Response:** I'll create an API testing agent for your project.

*[PM calls Claude MPM internal API]*

*[PM starts new claude-mpm session for validation]*

**Startup Output:**
```
🚀 Claude MPM Starting...
📦 Loading agents:
  ✅ research (system)
  ✅ engineer (system)  
  ✅ qa (system)
  ✅ api_testing_agent (project) ← New custom agent
📋 Ready for multi-agent coordination
```

**PM:** ✅ Custom agent created successfully! The API testing agent is now available in your workflow.

**User:** Perfect! Now I can delegate API testing tasks to the specialized agent.

### Example 2: Document-Based Agent Creation

**User:** "Create an agent based on the requirements in ./docs/database-agent-spec.md"

**PM Response:** I'll analyze the specification document and create your database agent.

*[PM reads specification document]*
*[PM extracts requirements and calls API]*
*[PM validates with new session]*

**Startup Output:**
```
🚀 Claude MPM Starting...
📄 Custom agents from specifications:
  ✅ db_optimization_agent (project) - Database performance specialist
📋 Workflow ready with custom database expertise
```

**PM:** ✅ Database optimization agent created from your specification! It's now available for database-related tasks.

### Example 3: Custom Workflow Creation

**User:** "Create a workflow where we always do research first, then get approval before any implementation"

**PM Response:** I'll create an approval-based development workflow for your project.

*[PM analyzes workflow requirements]*
*[PM generates custom instruction sections]*
*[PM rebuilds INSTRUCTIONS.md]*
*[PM validates with new session]*

**Startup Output:**
```
🚀 Claude MPM Starting...
📋 Custom Workflow: Approval-Based Development
  ✓ Research phase (always first)
  ⏳ Approval gate (before implementation)
  ✓ Implementation (after approval)
✅ Ready with custom workflow protocol
```

**PM:** ✅ Custom workflow active! All implementation tasks now require approval after research phase.

### Example 4: CLI Backup Access

```bash
# Users can also access functionality via CLI
# ⚠️ SUGGESTION ONLY - Must match existing CLI patterns

# Create agent via CLI
claude-mpm agent create "Testing specialist with Selenium knowledge"

# Create workflow via CLI  
claude-mpm workflow create "Agile sprint workflow with daily standups"

# List current configuration
claude-mpm config status

# Rebuild instructions
claude-mpm config rebuild
```

This design creates a user-friendly system where Claude Code's PM handles all the complexity, and users simply describe what they want. The PM validates its work by starting fresh sessions, making the process transparent and self-verifying.