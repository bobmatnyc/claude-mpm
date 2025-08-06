# Memory System Developer Guide

Comprehensive guide for developers working with the Claude MPM Agent Memory System.

## Overview

The Agent Memory System enables persistent learning across agent sessions, allowing agents to accumulate project-specific knowledge, patterns, and insights over time. This guide covers the internal architecture, APIs, and extension points for developers working with or extending the memory system.

## Architecture Components

### Core Services

```
src/claude_mpm/services/
├── agent_memory_manager.py     # Main memory management service
├── memory_router.py           # Content routing to appropriate agents
├── memory_builder.py          # Documentation processing and memory building
├── memory_optimizer.py        # Memory optimization and cleanup
└── project_analyzer.py        # Project analysis for contextual memory generation
```

### AgentMemoryManager

Central service for all memory operations.

```python
from claude_mpm.services.agent_memory_manager import AgentMemoryManager

# Initialize with configuration
manager = AgentMemoryManager(config, working_directory)

# Load agent memory
memory_content = manager.load_agent_memory("engineer")

# Add new learning
success = manager.update_agent_memory("engineer", "Implementation Guidelines", 
                                     "Use dependency injection pattern")

# Get system status
status = manager.get_memory_status()
```

**Key Methods:**
- `load_agent_memory(agent_id)`: Load memory for specific agent
- `update_agent_memory(agent_id, section, content)`: Add new learning to section
- `add_learning(agent_id, learning_type, content)`: Add structured learning
- `optimize_memory(agent_id=None)`: Optimize memory files
- `get_memory_status()`: Get comprehensive system status

### MemoryRouter

Routes memory commands to appropriate agents based on content analysis.

```python
from claude_mpm.services.memory_router import MemoryRouter

router = MemoryRouter(config)

# Analyze content and determine target agent
result = router.analyze_and_route("Use pytest for unit testing")
# Returns: target_agent="qa", section="Testing Strategies", confidence=0.87
```

**Supported Agents:**
- `engineer`: Implementation, coding, architecture
- `research`: Analysis, investigation, domain knowledge
- `qa`: Testing, quality assurance, validation
- `documentation`: Technical writing, guides
- `security`: Security analysis, compliance
- `pm`: Project management, coordination
- `data_engineer`: Data pipelines, AI APIs, analytics
- `test_integration`: Integration testing, E2E workflows
- `ops`: Infrastructure, deployment, monitoring
- `version_control`: Git workflows, release management

### ProjectAnalyzer

Analyzes project characteristics for contextual memory generation.

```python
from claude_mpm.services.project_analyzer import ProjectAnalyzer

analyzer = ProjectAnalyzer(config, working_directory)
characteristics = analyzer.analyze_project()

# Get project summary for memory templates
context_summary = analyzer.get_project_context_summary()

# Get important files for memory building
important_files = analyzer.get_important_files_for_context()
```

**Analysis Capabilities:**
- Technology stack detection from config files
- Directory structure analysis
- Framework and library identification  
- Testing framework detection
- Database and API pattern recognition
- Documentation file discovery

## Memory File Format

Memory files follow a structured Markdown format with enforced limits and sections:

```markdown
# Agent Memory: Engineer - MyProject

<!-- MEMORY LIMITS: 8KB max | 10 sections max | 15 items per section -->
<!-- Last Updated: 2025-08-06 10:30:15 | Auto-updated by: engineer -->

## Project Context
MyProject: React TypeScript SPA with Node.js backend
- Tech stack: React, TypeScript, Node.js, Express, PostgreSQL
- Architecture: Single Page Application with REST API

## Project Architecture
- Component-based architecture with atomic design principles
- State management using Redux Toolkit
- API layer with axios service abstractions
- Database: PostgreSQL with Prisma ORM

## Coding Patterns Learned
- Use functional components with hooks pattern
- Implement custom hooks for complex state logic
- Follow strict TypeScript configuration
- Error boundaries for component error handling

## Implementation Guidelines
- All API calls go through service layer abstraction
- Use React.memo for performance optimization
- Implement proper loading states and error handling
- Follow ESLint and Prettier configurations

## Common Mistakes to Avoid
- Don't mutate state directly - use Redux actions
- Avoid inline styles - use CSS modules or styled-components
- Don't skip error handling in async operations

## Current Technical Context
- Node.js v18+ required for development
- Uses Vite for build tooling and development server
- Testing with Jest and React Testing Library
- CI/CD pipeline with GitHub Actions
```

### Memory Limits and Constraints

```python
DEFAULT_MEMORY_LIMITS = {
    'max_file_size_kb': 8,           # 8KB default (~2000 tokens)
    'max_sections': 10,              # Maximum sections per file
    'max_items_per_section': 15,     # Maximum items per section
    'max_line_length': 120           # Maximum characters per line
}
```

**Agent-Specific Overrides:**
```yaml
# In .claude-mpm/config.yml
memory:
  agent_overrides:
    research:
      size_kb: 12  # Research agent gets more memory
    documentation:
      size_kb: 16  # Documentation agent needs extensive memory
```

## Extending the Memory System

### Adding New Agent Types

1. **Update MemoryRouter patterns:**

```python
# In memory_router.py
AGENT_PATTERNS = {
    'new_agent': {
        'keywords': [
            'new', 'agent', 'specific', 'keywords'
        ],
        'sections': [
            'New Agent Section 1',
            'New Agent Section 2'
        ]
    }
}
```

2. **Add agent-specific memory generation:**

```python
# In agent_memory_manager.py
def _generate_domain_knowledge_starters(self, characteristics, agent_id: str) -> str:
    if 'new_agent' in agent_id.lower():
        items.append("- Focus on new agent specific patterns")
    return '\n'.join(items)
```

### Custom Memory Hooks

Create hooks that integrate with the memory system:

```python
from claude_mpm.hooks.base_hook import PreDelegationHook
from claude_mpm.services.agent_memory_manager import get_memory_manager

class CustomMemoryHook(PreDelegationHook):
    def __init__(self):
        super().__init__(name="custom_memory", priority=25)
        self.memory_manager = get_memory_manager()
    
    def execute(self, context: HookContext) -> HookResult:
        agent_id = context.data.get('agent')
        
        # Load and inject specific memory sections
        memory_content = self.memory_manager.load_agent_memory(agent_id)
        context.data['custom_memory'] = self.extract_relevant_sections(memory_content)
        
        return HookResult(success=True, modified=True, data=context.data)
```

### Custom Memory Builders

Extend the memory building system to process custom file types:

```python
from claude_mpm.services.memory_builder import MemoryBuilder

class CustomMemoryBuilder(MemoryBuilder):
    def process_custom_files(self, file_patterns: List[str]) -> Dict[str, Any]:
        """Process custom file types for memory extraction."""
        results = {}
        
        for pattern in file_patterns:
            files = self.working_directory.glob(pattern)
            for file_path in files:
                # Custom processing logic
                extracted_content = self.extract_custom_content(file_path)
                routed_content = self.route_to_agents(extracted_content)
                results[str(file_path)] = routed_content
        
        return results
```

## Configuration Options

### Memory System Configuration

```yaml
# .claude-mpm/config.yml
memory:
  enabled: true                    # Enable/disable memory system
  auto_learning: true             # Enable automatic learning extraction
  
  limits:
    default_size_kb: 8            # Default memory file size limit
    max_sections: 10              # Maximum sections per memory file
    max_items_per_section: 15     # Maximum items per section
    max_line_length: 120          # Maximum line length
  
  agent_overrides:
    engineer:
      size_kb: 12                 # Engineer gets 12KB
      auto_learning: true
    research:
      size_kb: 16                 # Research gets 16KB
      auto_learning: true
    qa:
      size_kb: 8
      auto_learning: false        # Manual learning only
```

### Hook Integration

```yaml
hooks:
  memory_integration: true        # Enable memory hooks
  
  custom_hooks:
    - name: "custom_memory"
      path: "path/to/custom_hook.py"
      priority: 25
```

## API Reference

### AgentMemoryManager API

**Configuration and Initialization:**
```python
manager = AgentMemoryManager(
    config=Config(),              # Optional config object
    working_directory=Path(".")   # Optional working directory
)
```

**Core Memory Operations:**
```python
# Loading and updating memory
content = manager.load_agent_memory(agent_id: str) -> str
success = manager.update_agent_memory(agent_id: str, section: str, content: str) -> bool
success = manager.add_learning(agent_id: str, learning_type: str, content: str) -> bool

# System operations
status = manager.get_memory_status() -> Dict[str, Any]
result = manager.optimize_memory(agent_id: Optional[str] = None) -> Dict[str, Any]
result = manager.build_memories_from_docs(force_rebuild: bool = False) -> Dict[str, Any]

# Analysis operations
routing = manager.route_memory_command(content: str, context: Optional[Dict] = None) -> Dict[str, Any]
cross_refs = manager.cross_reference_memories(query: Optional[str] = None) -> Dict[str, Any]
raw_data = manager.get_all_memories_raw() -> Dict[str, Any]
```

### MemoryRouter API

**Routing and Analysis:**
```python
router = MemoryRouter(config)

# Core routing
result = router.analyze_and_route(content: str, context: Optional[Dict] = None) -> Dict[str, Any]

# Utility methods
agents = router.get_supported_agents() -> List[str]
supported = router.is_agent_supported(agent_type: str) -> bool
patterns = router.get_routing_patterns() -> Dict[str, Any]

# Testing
results = router.test_routing_patterns(test_cases: List[Dict[str, str]]) -> List[Dict[str, Any]]
```

### CLI Integration

**Memory Commands:**
```bash
# System status and management
claude-mpm memory status
claude-mpm memory init

# Viewing memories
claude-mpm memory show [agent_id] [--format summary|detailed] [--raw]
claude-mpm memory cross-ref [--query "search term"]

# Adding and managing content
claude-mpm memory add <agent_id> <type> "content"
claude-mpm memory optimize [agent_id]
claude-mpm memory build [--force-rebuild]

# Testing and debugging
claude-mpm memory route --content "content to analyze"
```

## Performance Considerations

### Memory File Size Management

- **Default 8KB limit**: Balances comprehensive storage with prompt efficiency
- **Auto-truncation**: Removes oldest items when limits exceeded
- **Section limits**: Maximum 10 sections, 15 items per section
- **Line length limits**: 120 characters per line item

### Optimization Strategies

1. **Regular optimization**: Run `memory optimize` periodically
2. **Duplicate detection**: 85% similarity threshold for removal  
3. **Consolidation**: 70% similarity threshold for merging related items
4. **Priority reordering**: High-priority items moved to top

### Caching and Performance

- **Project analysis caching**: Analysis results cached until project changes detected
- **Memory file caching**: In-memory caching of frequently accessed files
- **Lazy loading**: Memory content loaded only when needed

## Testing and Validation

### Unit Testing Memory Components

```python
import pytest
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.memory_router import MemoryRouter

def test_memory_routing():
    router = MemoryRouter()
    result = router.analyze_and_route("Use pytest for unit testing")
    
    assert result['target_agent'] == 'qa'
    assert result['confidence'] > 0.5
    assert 'pytest' in str(result['reasoning']).lower()

def test_memory_update():
    manager = AgentMemoryManager()
    success = manager.update_agent_memory(
        'engineer', 
        'Implementation Guidelines', 
        'Always use type hints in Python'
    )
    
    assert success is True
    
    # Verify content was added
    memory = manager.load_agent_memory('engineer')
    assert 'type hints' in memory.lower()
```

### Integration Testing

```python
def test_memory_system_integration():
    """Test complete memory workflow."""
    manager = AgentMemoryManager()
    
    # Test memory creation
    memory = manager.load_agent_memory('test_agent')
    assert memory is not None
    
    # Test learning addition
    success = manager.add_learning('test_agent', 'pattern', 'Test learning item')
    assert success is True
    
    # Test optimization
    result = manager.optimize_memory('test_agent')
    assert result.get('success') is True
    
    # Test cross-referencing
    cross_refs = manager.cross_reference_memories()
    assert isinstance(cross_refs, dict)
```

## Troubleshooting

### Common Issues

**Memory Files Not Updating:**
```python
# Check system status
status = manager.get_memory_status()
print(f"System enabled: {status['system_enabled']}")
print(f"Auto learning: {status['auto_learning']}")

# Verify file permissions
import os
memory_dir = manager.memories_dir
print(f"Directory writable: {os.access(memory_dir, os.W_OK)}")
```

**Routing Issues:**
```python
# Test routing logic
router = MemoryRouter()
test_cases = [
    {"content": "Use pytest for testing", "expected_agent": "qa"},
    {"content": "Implement REST API endpoints", "expected_agent": "engineer"}
]

results = router.test_routing_patterns(test_cases)
for result in results:
    print(f"Content: {result['content']}")
    print(f"Expected: {result['expected_agent']}")
    print(f"Actual: {result['actual_agent']}")
    print(f"Correct: {result['correct']}")
```

**Performance Issues:**
```bash
# Check memory file sizes
claude-mpm memory status

# Optimize if needed
claude-mpm memory optimize

# Force rebuild if corrupted
claude-mpm memory build --force-rebuild
```

### Debug Logging

Enable debug logging for memory operations:

```python
import logging
logging.getLogger('claude_mpm.services.agent_memory_manager').setLevel(logging.DEBUG)
logging.getLogger('claude_mpm.services.memory_router').setLevel(logging.DEBUG)
```

## Best Practices

### Memory Content Guidelines

1. **Keep items concise**: Under 100 characters per item
2. **Focus on actionable insights**: Avoid descriptive content
3. **Use consistent terminology**: Maintain project-specific vocabulary
4. **Prioritize recent learnings**: Remove outdated information

### Agent Assignment

1. **Follow routing patterns**: Use established keywords for consistency
2. **Agent specialization**: Assign content to most relevant agent
3. **Cross-agent sharing**: Duplicate critical information when needed
4. **Context specificity**: Include project-specific details

### System Maintenance

1. **Regular optimization**: Weekly or monthly optimization runs
2. **Memory monitoring**: Track file sizes and usage patterns
3. **Content review**: Periodic manual review of agent memories
4. **Backup strategy**: Version control memory files with project

## Migration and Upgrades

### Upgrading Memory System

When upgrading memory system components:

1. **Backup existing memories**: Copy `.claude-mpm/memories/` directory
2. **Check configuration compatibility**: Review config schema changes
3. **Test routing patterns**: Verify agent routing still works correctly
4. **Validate memory formats**: Ensure files still parse correctly

### Migrating Between Versions

```bash
# Backup current memories
cp -r .claude-mpm/memories .claude-mpm/memories.backup

# Update to new version
pip install --upgrade claude-mpm

# Validate memory system
claude-mpm memory status

# Rebuild if needed
claude-mpm memory build --force-rebuild
```

This comprehensive developer guide provides the foundation for working with, extending, and maintaining the Claude MPM Agent Memory System.