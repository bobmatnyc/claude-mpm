# Framework Generator and Agent Loader Analysis

Date: 2025-01-24

## Executive Summary

The claude-mpm codebase has well-structured components but suffers from multiple parallel implementations of agent loading and some hardcoded file references that need updating for the INSTRUCTIONS.md transition.

## Current Architecture

### Framework Generator (`framework_claude_md_generator/`)

**Purpose**: Generates the framework INSTRUCTIONS.md/CLAUDE.md template with auto-versioning and deployment capabilities.

**Components**:
- `VersionManager`: Handles version numbering (framework version from VERSION files)
- `ContentValidator`: Validates template content structure
- `ContentAssembler`: Assembles sections and applies template variables
- `DeploymentManager`: Deploys to parent directories with version comparison
- `SectionManager`: Manages ordered sections
- Section generators in `section_generators/` directory

**Code Path**:
1. `FrameworkClaudeMdGenerator.generate()` called
2. Version manager auto-increments version if current content provided
3. Section manager gets all sections in order
4. Each section generator creates its content
5. Content assembler combines sections and applies variables
6. Deployment manager writes to target directory

### Agent Loader Systems

#### 1. Main Agent Loader (`agents/agent_loader.py`)

**Purpose**: Primary agent loading with model selection and caching.

**Features**:
- Loads from `framework/agent-roles/*.md` files
- Hardcoded agent name mappings
- Dynamic model selection based on task complexity
- SharedPromptCache integration (99.7% performance improvement)
- Backward-compatible functions

**Code Path**:
```python
get_agent_prompt(agent_name) ->
  load_agent_prompt_from_md() ->
    Check cache ->
    Load from MD file ->
    Cache content ->
  Analyze task complexity (optional) ->
  Get model configuration ->
  Prepend base instructions ->
  Return prompt (+ model info if requested)
```

#### 2. Framework Agent Loader (`services/framework_agent_loader.py`)

**Purpose**: Hierarchical agent loading with precedence.

**Features**:
- Project → Framework (user → trained → system) precedence
- Separate from main agent loader
- Profile-based loading from `.claude-pm/agents/` directories

**Issues**:
- Still references CLAUDE.md instead of INSTRUCTIONS.md
- Not integrated with main agent loader
- Duplicate implementation

#### 3. Agent Registry Adapter (`core/agent_registry.py`)

**Purpose**: Integration point for agent registry.

**Features**:
- SimpleAgentRegistry as temporary implementation
- Framework path discovery
- Agent discovery from directories

**Issues**:
- Not connected to actual agent loading
- Simplified implementation doesn't match framework capabilities

## Key Issues Found

### 1. File Name Inconsistencies
- `deployment_manager.py` still hardcoded to write to "CLAUDE.md"
- `framework_agent_loader.py` still looks for "CLAUDE.md"
- Need configurable target filename

### 2. Multiple Agent Loading Implementations
- Three separate systems that don't share code
- Different approaches to agent discovery
- No unified interface

### 3. Hardcoded Agent Mappings
- Agent names to MD files hardcoded in dictionary
- Limits extensibility for custom agents
- No dynamic discovery

### 4. Complex Model Selection
- Overly complex with multiple environment variables
- Could be simplified into separate service
- Too tightly coupled with agent loading

## Recommendations

### 1. Immediate Fixes

```python
# deployment_manager.py - Make target filename configurable
class DeploymentManager:
    def __init__(self, version_manager, validator, target_filename="INSTRUCTIONS.md"):
        self.target_filename = target_filename
        # ...
    
    def deploy_to_parent(self, content, parent_path, force=False):
        target_file = parent_path / self.target_filename
        # Check for legacy CLAUDE.md if INSTRUCTIONS.md doesn't exist
        if not target_file.exists():
            legacy_file = parent_path / "CLAUDE.md"
            if legacy_file.exists():
                target_file = legacy_file
```

### 2. Unify Agent Loading

Create a unified agent loader that combines the best of all three systems:

```python
class UnifiedAgentLoader:
    """Unified agent loading with hierarchy, caching, and model selection."""
    
    def __init__(self):
        self.cache = SharedPromptCache.get_instance()
        self.hierarchy = ['project', 'user', 'system']
        self.model_selector = ModelSelector()
        
    def load_agent(self, agent_name: str, context: dict = None) -> AgentDefinition:
        """Load agent with full hierarchy support."""
        # Check cache
        cached = self.cache.get(f"agent:{agent_name}")
        if cached:
            return cached
            
        # Search hierarchy
        for level in self.hierarchy:
            agent = self._load_from_level(agent_name, level)
            if agent:
                # Analyze complexity if context provided
                if context:
                    model = self.model_selector.select_model(agent, context)
                    agent.selected_model = model
                
                # Cache and return
                self.cache.set(f"agent:{agent_name}", agent)
                return agent
                
        raise AgentNotFoundError(f"Agent {agent_name} not found")
```

### 3. Dynamic Agent Discovery

Replace hardcoded mappings with dynamic discovery:

```python
def discover_agents(directory: Path) -> Dict[str, AgentInfo]:
    """Dynamically discover agents from directory."""
    agents = {}
    
    for md_file in directory.glob("**/*.md"):
        # Extract agent name from filename
        agent_name = md_file.stem.replace('-agent', '').replace('-', '_')
        
        # Parse front matter for metadata
        content = md_file.read_text()
        metadata = parse_front_matter(content)
        
        agents[agent_name] = AgentInfo(
            name=agent_name,
            file=md_file,
            type=metadata.get('type', 'generic'),
            specializations=metadata.get('specializations', []),
            default_model=metadata.get('model', 'sonnet')
        )
    
    return agents
```

### 4. Simplify Model Selection

Extract model selection into a separate service:

```python
class ModelSelector:
    """Simple model selection based on task complexity."""
    
    def select_model(self, agent: AgentDefinition, context: dict) -> str:
        # Simple rules-based selection
        if context.get('complexity_score', 50) > 70:
            return 'opus'
        elif agent.type in ['documentation', 'qa']:
            return 'sonnet'
        else:
            return agent.default_model or 'sonnet'
```

### 5. Configuration-Driven Approach

Use configuration files instead of hardcoded values:

```yaml
# agent_config.yaml
agents:
  documentation:
    file: documentation-agent.md
    default_model: sonnet
    specializations: [docs, changelog]
    
  engineer:
    file: engineer-agent.md
    default_model: opus
    specializations: [code, implementation]

framework:
  target_file: INSTRUCTIONS.md
  legacy_file: CLAUDE.md
  version_format: serial  # or semantic
```

## Integration Points

### Current Integration Flow

```
Orchestrator
  └── FrameworkLoader
      └── AgentRegistryAdapter
          └── SimpleAgentRegistry (temporary)

Separate:
- agent_loader.py (used by claude-multiagent-pm)
- framework_agent_loader.py (standalone)
- framework_claude_md_generator (standalone)
```

### Recommended Integration Flow

```
Orchestrator
  └── FrameworkLoader
      └── UnifiedAgentLoader
          ├── AgentDiscovery (dynamic)
          ├── HierarchyManager (project/user/system)
          ├── ModelSelector (simplified)
          └── SharedPromptCache (performance)

FrameworkGenerator
  └── Uses UnifiedAgentLoader for agent info
  └── Configurable target filenames
```

## Performance Considerations

1. **SharedPromptCache** is working well - maintain this
2. **Agent discovery** should be cached after first scan
3. **Model selection** should be optional and lightweight
4. **File I/O** should be minimized with proper caching

## Migration Plan

1. **Phase 1**: Update hardcoded CLAUDE.md references
2. **Phase 2**: Create UnifiedAgentLoader as new implementation
3. **Phase 3**: Migrate existing code to use UnifiedAgentLoader
4. **Phase 4**: Deprecate old implementations
5. **Phase 5**: Remove deprecated code

## Conclusion

The codebase shows good modularity but needs consolidation of the multiple agent loading approaches. The framework generator is well-structured but needs minor updates for INSTRUCTIONS.md support. With the recommended changes, the system will be more maintainable and extensible.