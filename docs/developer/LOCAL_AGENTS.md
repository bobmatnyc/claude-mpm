# Local Agents Developer Guide

Complete developer reference for implementing, extending, and integrating with the Claude MPM local agent system.

## Architecture Overview

The local agent system extends Claude MPM's agent framework with customizable, project-specific agents stored as JSON templates. The system provides full lifecycle management from creation to deployment with proper priority resolution.

### Key Components

```
src/claude_mpm/services/agents/
├── local_template_manager.py           # Core template management
├── deployment/
│   └── local_template_deployment.py    # Deployment and synchronization
└── loading/
    └── base_agent_manager.py           # Base agent management
```

### Data Flow

```
Local JSON Template → LocalAgentTemplate → Deployment → Claude Code Integration
     ↓                      ↓                   ↓                ↓
Template Discovery → Validation → Priority Resolution → Runtime Loading
```

## LocalAgentTemplateManager API

### Class Overview

```python
from claude_mpm.services.agents.local_template_manager import LocalAgentTemplateManager

manager = LocalAgentTemplateManager(working_directory=Path.cwd())
```

The `LocalAgentTemplateManager` is the primary interface for local agent operations.

### Core Methods

#### Template Discovery

```python
def discover_local_templates(self, force_refresh: bool = False) -> Dict[str, LocalAgentTemplate]:
    """Discover all local agent templates.
    
    Args:
        force_refresh: Force re-discovery even if cache is valid
        
    Returns:
        Dictionary mapping agent IDs to LocalAgentTemplate objects
    """
```

**Usage:**
```python
# Discover with caching
templates = manager.discover_local_templates()

# Force refresh cache
templates = manager.discover_local_templates(force_refresh=True)

# Access specific template
researcher = templates.get("custom-researcher")
```

#### Template Creation

```python
def create_local_template(
    self,
    agent_id: str,
    name: str,
    description: str,
    instructions: str,
    model: str = "sonnet",
    tools: Union[str, List[str]] = "*",
    parent_agent: Optional[str] = None,
    tier: str = "project"
) -> LocalAgentTemplate:
```

**Usage:**
```python
# Basic template creation
template = manager.create_local_template(
    agent_id="domain-expert",
    name="Domain Expert",
    description="Expert in our business domain",
    instructions="You are an expert in financial analysis...",
    model="sonnet",
    tools="*"
)

# Template with inheritance
template = manager.create_local_template(
    agent_id="custom-researcher",
    name="Custom Researcher",
    description="Enhanced research capabilities",
    instructions="Enhanced research with domain focus...",
    parent_agent="research"
)
```

#### Template Persistence

```python
def save_local_template(self, template: LocalAgentTemplate, tier: Optional[str] = None) -> Path:
    """Save template to appropriate directory."""

def delete_local_template(self, agent_id: str) -> bool:
    """Delete template from all tiers."""

def get_local_template(self, agent_id: str) -> Optional[LocalAgentTemplate]:
    """Retrieve specific template."""
```

#### Template Operations

```python
def validate_local_template(self, template: LocalAgentTemplate) -> Tuple[bool, List[str]]:
    """Validate template and return errors if any."""

def version_local_template(self, agent_id: str, new_version: str) -> Optional[Path]:
    """Create versioned backup and update template."""

def inherit_from_system_agent(
    self, 
    system_agent_id: str, 
    new_agent_id: str, 
    modifications: Dict[str, Any]
) -> LocalAgentTemplate:
    """Create local agent inheriting from system agent."""
```

#### Import/Export

```python
def export_local_templates(self, output_dir: Path) -> int:
    """Export all templates to directory."""

def import_local_templates(self, input_dir: Path, tier: str = "project") -> int:
    """Import templates from directory."""
```

## LocalAgentTemplate Data Model

### Core Schema

```python
@dataclass
class LocalAgentTemplate:
    schema_version: str = "1.3.0"
    agent_id: str = ""
    agent_version: str = "1.0.0" 
    author: str = ""
    agent_type: str = ""
    
    metadata: Dict[str, Any] = None
    capabilities: Dict[str, Any] = None
    instructions: str = ""
    configuration: Dict[str, Any] = None
    
    # Local-specific fields
    tier: str = "project"
    priority: int = 1000
    is_local: bool = True
    parent_agent: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

### JSON Serialization

```python
# Convert to JSON
json_data = template.to_json()

# Create from JSON
template = LocalAgentTemplate.from_json(json_data)
```

### Template Validation Rules

```python
def validate_local_template(self, template: LocalAgentTemplate) -> Tuple[bool, List[str]]:
    errors = []
    
    # Required fields
    if not template.agent_id:
        errors.append("agent_id is required")
    if not template.instructions:
        errors.append("instructions are required")
    if not template.metadata.get("name"):
        errors.append("metadata.name is required")
        
    # Model validation
    valid_models = ["opus", "sonnet", "haiku"]
    model = template.capabilities.get("model")
    if model and model not in valid_models:
        errors.append(f"Invalid model: {model}")
        
    # Reserved names
    reserved_ids = ["pm", "project-manager", "claude-mpm"]
    if template.agent_id in reserved_ids:
        errors.append(f"Reserved agent ID: {template.agent_id}")
        
    return len(errors) == 0, errors
```

## Priority System Implementation

### Priority Levels

```python
# Priority constants
PROJECT_PRIORITY = 2000  # Highest
USER_PRIORITY = 1500     # Medium  
SYSTEM_PRIORITY = 1000   # Lowest (default)
```

### Resolution Algorithm

```python
def resolve_agent_priority(agent_id: str) -> Optional[LocalAgentTemplate]:
    """Resolve agent using priority hierarchy."""
    
    # Check project level first (highest priority)
    project_template = load_project_template(agent_id)
    if project_template and project_template.priority >= PROJECT_PRIORITY:
        return project_template
        
    # Check user level
    user_template = load_user_template(agent_id)  
    if user_template and user_template.priority >= USER_PRIORITY:
        return user_template
        
    # Fall back to system agents
    return load_system_template(agent_id)
```

## Deployment Service

### LocalTemplateDeploymentService

```python
from claude_mpm.services.agents.deployment.local_template_deployment import (
    LocalTemplateDeploymentService
)

service = LocalTemplateDeploymentService()
```

#### Core Deployment Methods

```python
def deploy_local_templates(
    self, 
    force: bool = False, 
    tier_filter: Optional[str] = None
) -> Dict[str, List[str]]:
    """Deploy all local templates to Claude Code.
    
    Returns:
        Dictionary with 'deployed', 'updated', 'skipped', 'errors' lists
    """

def deploy_single_local_template(self, agent_id: str, force: bool = False) -> bool:
    """Deploy specific local template."""

def sync_local_templates(self) -> Dict[str, List[str]]:
    """Synchronize local templates with deployed agents."""
```

#### Deployment Process

1. **Template Discovery**: Find all local JSON templates
2. **Validation**: Ensure templates are valid and deployable
3. **Conversion**: Convert JSON templates to Claude Code format (.md files)
4. **Deployment**: Copy to `.claude/agents/` with proper metadata
5. **Registration**: Register with Claude Code's agent loader

```python
# Example deployment flow
def deploy_template(template: LocalAgentTemplate) -> bool:
    try:
        # Validate template
        is_valid, errors = validate_template(template)
        if not is_valid:
            raise ValueError(f"Invalid template: {errors}")
            
        # Convert to Claude Code format
        markdown_content = convert_to_markdown(template)
        
        # Write to deployment directory
        deploy_path = get_claude_agents_dir() / f"{template.agent_id}.md"
        deploy_path.write_text(markdown_content)
        
        # Update metadata
        update_agent_metadata(template)
        
        return True
    except Exception as e:
        logger.error(f"Deployment failed: {e}")
        return False
```

## CLI Integration

### Command Structure

The CLI commands are implemented in `src/claude_mpm/cli/commands/agent_manager.py`:

```python
class AgentManagerCommand(AgentCommand):
    def _create_local_agent(self, args) -> CommandResult:
        """Create local agent template."""
        
    def _deploy_local_agents(self, args) -> CommandResult:
        """Deploy local templates to Claude Code."""
        
    def _list_local_agents(self, args) -> CommandResult:
        """List all local agent templates."""
        
    def _sync_local_agents(self, args) -> CommandResult:
        """Synchronize templates with deployed agents."""
```

### Argument Parsing

```python
# In agent_manager_parser.py
def add_local_agent_commands(parser):
    # Create local agent
    create_local = subparsers.add_parser('create-local')
    create_local.add_argument('--agent-id', required=True)
    create_local.add_argument('--name')
    create_local.add_argument('--description')
    create_local.add_argument('--instructions')
    create_local.add_argument('--model', choices=['opus', 'sonnet', 'haiku'])
    create_local.add_argument('--tools')
    create_local.add_argument('--parent')
    create_local.add_argument('--tier', choices=['project', 'user'])
    
    # Deploy local agents
    deploy_local = subparsers.add_parser('deploy-local')
    deploy_local.add_argument('--agent-id')
    deploy_local.add_argument('--force', action='store_true')
    deploy_local.add_argument('--tier', choices=['project', 'user'])
```

## File System Layout

### Local Agent Directories

```
Project Level (.claude-mpm/agents/):
├── custom-researcher.json
├── domain-expert.json
├── versions/
│   ├── custom-researcher/
│   │   ├── 1.0.0.json
│   │   └── 1.1.0.json
│   └── domain-expert/
│       └── 1.0.0.json
└── .metadata
    └── discovery-cache.json

User Level (~/.claude-mpm/agents/):
├── personal-assistant.json
├── code-reviewer.json
└── versions/
    └── ...

Deployment Target (.claude/agents/):
├── custom-researcher.md
├── domain-expert.md
└── personal-assistant.md
```

### Template File Format

```json
{
  "schema_version": "1.3.0",
  "agent_id": "custom-researcher",
  "agent_version": "1.2.0",
  "author": "my-project",
  "agent_type": "custom-researcher",
  "metadata": {
    "name": "Custom Research Assistant",
    "description": "Specialized research agent for financial analysis",
    "tier": "project",
    "tags": ["local", "custom", "finance", "research"],
    "specializations": ["financial-modeling", "risk-analysis"],
    "category": "research"
  },
  "capabilities": {
    "model": "sonnet",
    "tools": "*",
    "max_context": 200000,
    "supports_multimodal": true
  },
  "instructions": "You are a specialized research assistant...",
  "configuration": {
    "temperature": 0.7,
    "max_tokens": 4096,
    "timeout": 120
  },
  "priority": 2000,
  "parent_agent": "research",
  "created_at": "2024-09-06T10:30:00Z",
  "updated_at": "2024-09-06T15:45:00Z"
}
```

## Integration Points

### Framework Loader Integration

```python
# In framework_loader.py
def load_local_agents() -> Dict[str, Any]:
    """Load local agents for framework integration."""
    manager = LocalAgentTemplateManager()
    templates = manager.discover_local_templates()
    
    # Convert to framework format
    agents = {}
    for agent_id, template in templates.items():
        agents[agent_id] = {
            "name": template.metadata.get("name", agent_id),
            "instructions": template.instructions,
            "model": template.capabilities.get("model", "sonnet"),
            "tools": template.capabilities.get("tools", "*"),
            "priority": template.priority,
            "is_local": True
        }
    
    return agents
```

### Agent Loader Integration

```python
# Agent discovery hook
def discover_agents() -> List[AgentInfo]:
    agents = []
    
    # Add system agents
    agents.extend(discover_system_agents())
    
    # Add local agents (with priority)
    local_manager = LocalAgentTemplateManager()
    local_templates = local_manager.discover_local_templates()
    
    for template in local_templates.values():
        agents.append(AgentInfo(
            id=template.agent_id,
            name=template.metadata.get("name"),
            description=template.metadata.get("description"),
            priority=template.priority,
            tier=template.tier,
            is_local=True,
            source_path=get_template_path(template)
        ))
    
    # Sort by priority (highest first)
    agents.sort(key=lambda a: a.priority, reverse=True)
    return agents
```

## Extension Points

### Custom Template Processors

```python
class CustomTemplateProcessor:
    """Custom processor for specialized template types."""
    
    def process_template(self, template: LocalAgentTemplate) -> LocalAgentTemplate:
        """Apply custom processing logic."""
        
        # Add custom metadata
        template.metadata["processed_by"] = "CustomProcessor"
        template.metadata["processing_version"] = "1.0"
        
        # Apply transformations
        if template.parent_agent:
            template = self.inherit_capabilities(template)
            
        return template
    
    def inherit_capabilities(self, template: LocalAgentTemplate) -> LocalAgentTemplate:
        """Inherit capabilities from parent agent."""
        parent = self.load_parent_template(template.parent_agent)
        if parent:
            # Merge capabilities
            merged_capabilities = {**parent.capabilities, **template.capabilities}
            template.capabilities = merged_capabilities
            
        return template

# Register processor
manager.register_processor("custom", CustomTemplateProcessor())
```

### Template Validators

```python
class DomainValidator:
    """Domain-specific template validation."""
    
    def validate(self, template: LocalAgentTemplate) -> Tuple[bool, List[str]]:
        errors = []
        
        # Domain-specific validations
        if "finance" in template.metadata.get("tags", []):
            if "financial" not in template.instructions.lower():
                errors.append("Finance agents must mention financial expertise")
                
        # Check required specializations
        if not template.metadata.get("specializations"):
            errors.append("Template must specify specializations")
            
        return len(errors) == 0, errors

# Register validator
manager.register_validator(DomainValidator())
```

## Testing Support

### Test Utilities

```python
# test_utils.py
def create_test_template(agent_id: str = "test-agent") -> LocalAgentTemplate:
    """Create a test template with valid defaults."""
    return LocalAgentTemplate(
        agent_id=agent_id,
        metadata={
            "name": f"Test Agent {agent_id}",
            "description": "Test agent for unit testing"
        },
        instructions="You are a test agent for unit testing.",
        capabilities={"model": "sonnet", "tools": "*"}
    )

def create_temp_agent_dir() -> Path:
    """Create temporary directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    (temp_dir / "agents").mkdir()
    return temp_dir
```

### Unit Test Examples

```python
import unittest
from pathlib import Path
from claude_mpm.services.agents.local_template_manager import LocalAgentTemplateManager

class TestLocalAgentTemplateManager(unittest.TestCase):
    
    def setUp(self):
        self.temp_dir = create_temp_agent_dir()
        self.manager = LocalAgentTemplateManager(working_directory=self.temp_dir)
    
    def test_create_template(self):
        template = self.manager.create_local_template(
            agent_id="test-agent",
            name="Test Agent",
            description="Test description",
            instructions="Test instructions"
        )
        
        self.assertEqual(template.agent_id, "test-agent")
        self.assertEqual(template.metadata["name"], "Test Agent")
        self.assertTrue(template.is_local)
    
    def test_save_and_load_template(self):
        template = create_test_template("save-test")
        
        # Save template
        saved_path = self.manager.save_local_template(template)
        self.assertTrue(saved_path.exists())
        
        # Load template
        loaded_template = self.manager.get_local_template("save-test")
        self.assertIsNotNone(loaded_template)
        self.assertEqual(loaded_template.agent_id, "save-test")
    
    def test_template_validation(self):
        # Valid template
        valid_template = create_test_template("valid")
        is_valid, errors = self.manager.validate_local_template(valid_template)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Invalid template (missing required fields)
        invalid_template = LocalAgentTemplate()
        is_valid, errors = self.manager.validate_local_template(invalid_template)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
```

### Integration Tests

```python
class TestLocalAgentIntegration(unittest.TestCase):
    
    def test_end_to_end_workflow(self):
        # Create manager
        manager = LocalAgentTemplateManager()
        
        # Create template
        template = manager.create_local_template(
            agent_id="integration-test",
            name="Integration Test Agent",
            description="End-to-end test agent",
            instructions="Integration test instructions"
        )
        
        # Validate template
        is_valid, errors = manager.validate_local_template(template)
        self.assertTrue(is_valid, f"Validation errors: {errors}")
        
        # Save template
        saved_path = manager.save_local_template(template)
        self.assertTrue(saved_path.exists())
        
        # Deploy template
        deployment_service = LocalTemplateDeploymentService()
        success = deployment_service.deploy_single_local_template("integration-test")
        self.assertTrue(success)
        
        # Verify deployment
        claude_agents_dir = Path.cwd() / ".claude" / "agents"
        deployed_file = claude_agents_dir / "integration-test.md"
        self.assertTrue(deployed_file.exists())
        
        # Clean up
        if deployed_file.exists():
            deployed_file.unlink()
        manager.delete_local_template("integration-test")
```

## Performance Considerations

### Caching Strategy

```python
class CachedTemplateManager(LocalAgentTemplateManager):
    """Template manager with enhanced caching."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._template_cache = {}
        self._cache_timestamps = {}
        self.cache_ttl = 300  # 5 minutes
    
    def discover_local_templates(self, force_refresh: bool = False) -> Dict[str, LocalAgentTemplate]:
        current_time = time.time()
        
        # Check cache validity
        if not force_refresh and self._cache_valid:
            last_update = self._cache_timestamps.get("discovery", 0)
            if current_time - last_update < self.cache_ttl:
                return self._template_cache
        
        # Refresh cache
        templates = super().discover_local_templates(force_refresh=True)
        self._cache_timestamps["discovery"] = current_time
        return templates
```

### Lazy Loading

```python
class LazyTemplateManager:
    """Template manager with lazy loading for better performance."""
    
    def __init__(self):
        self._templates: Dict[str, Optional[LocalAgentTemplate]] = {}
        self._loaded: Set[str] = set()
    
    def get_template(self, agent_id: str) -> Optional[LocalAgentTemplate]:
        """Get template with lazy loading."""
        if agent_id not in self._loaded:
            self._templates[agent_id] = self._load_template(agent_id)
            self._loaded.add(agent_id)
        
        return self._templates[agent_id]
    
    def _load_template(self, agent_id: str) -> Optional[LocalAgentTemplate]:
        """Load single template from disk."""
        for search_dir in [self.project_agents_dir, self.user_agents_dir]:
            template_file = search_dir / f"{agent_id}.json"
            if template_file.exists():
                with open(template_file) as f:
                    data = json.load(f)
                return LocalAgentTemplate.from_json(data)
        return None
```

## Security Considerations

### Template Validation

```python
def validate_security(template: LocalAgentTemplate) -> List[str]:
    """Security validation for templates."""
    warnings = []
    
    # Check for potentially dangerous instructions
    dangerous_patterns = [
        "system commands",
        "file operations",
        "network access",
        "execute shell"
    ]
    
    instructions_lower = template.instructions.lower()
    for pattern in dangerous_patterns:
        if pattern in instructions_lower:
            warnings.append(f"Potentially dangerous instruction pattern: {pattern}")
    
    # Validate tool access
    tools = template.capabilities.get("tools", "*")
    if tools == "*":
        warnings.append("Template grants access to all tools - consider restricting")
    
    return warnings
```

### Sandboxed Execution

```python
class SandboxedTemplateManager(LocalAgentTemplateManager):
    """Template manager with sandboxed operations."""
    
    def save_local_template(self, template: LocalAgentTemplate, tier: Optional[str] = None) -> Path:
        # Security validation
        security_warnings = validate_security(template)
        if security_warnings:
            logger.warning(f"Security warnings for {template.agent_id}: {security_warnings}")
        
        # Sanitize template content
        template = self.sanitize_template(template)
        
        return super().save_local_template(template, tier)
    
    def sanitize_template(self, template: LocalAgentTemplate) -> LocalAgentTemplate:
        """Sanitize template content for security."""
        # Remove potentially dangerous content
        template.instructions = self.sanitize_instructions(template.instructions)
        return template
```

This comprehensive developer guide provides all the technical details needed to work with, extend, and integrate the local agent system in Claude MPM.