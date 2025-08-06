# Complete Agent Memory System Documentation

Comprehensive reference covering all aspects of the Claude MPM Agent Memory System including recent enhancements, architecture, and usage patterns.

## System Overview

The Agent Memory System enables persistent learning and knowledge accumulation across agent sessions, transforming generic AI assistants into project-aware specialists that understand your codebase, conventions, and patterns.

### Core Capabilities

- **10 Specialized Agent Types** with dedicated memory sections and routing patterns
- **Project-Specific Memory Generation** through automated project analysis
- **Enhanced Routing Algorithm** with square root normalization and multi-word keyword bonuses
- **Dynamic Documentation Processing** with intelligent file discovery
- **Real-Time Learning Integration** via hook system
- **Comprehensive CLI Interface** for management and debugging

## Recent Enhancements (August 2025)

### New Agent Types

**Data Engineer Agent (`data_engineer`)**
- Specialized for data pipelines, database optimization, and AI API integrations
- Keywords include: data, pipeline, ETL, analytics, warehouse, streaming, AI API, OpenAI, Claude, LLM, embedding, vector database
- Memory sections: Database Architecture Patterns, Pipeline Design Strategies, Data Quality Standards, Performance Optimization Techniques

**Test Integration Agent (`test_integration`)**
- Focused on integration testing, E2E workflows, and cross-system validation
- Keywords include: integration, e2e, end-to-end, system test, workflow test, API test, contract test, Selenium, Cypress, Playwright
- Memory sections: Integration Test Patterns, Cross-System Validation, Test Environment Management, End-to-End Workflow Testing

### Algorithm Improvements

**Enhanced Routing Precision:**
```python
# Square root normalization prevents keyword-rich agents from being penalized
score = score / math.sqrt(len(patterns['keywords']))

# Multi-word keywords get bonus scoring for semantic relevance
bonus = 1.5 if ' ' in keyword else 1.0
score += bonus
```

**Context-Aware Adjustments:**
- Task type hints influence routing decisions
- Agent hints provide manual routing control
- Confidence scoring improved with 2x scaling factor

## Complete Agent Roster

### Core Development Agents

1. **Engineer** - Implementation patterns, coding standards, architecture decisions
2. **Research** - Analysis findings, domain knowledge, technical investigations  
3. **QA** - Testing strategies, quality standards, validation processes
4. **Documentation** - Technical writing, content organization, user guides

### Specialized Domain Agents

5. **Security** - Security patterns, compliance requirements, threat analysis
6. **PM** - Project coordination, team communication, process improvements
7. **Data Engineer** *(New)* - Data pipelines, AI APIs, analytics workflows
8. **Test Integration** *(New)* - Integration testing, E2E validation, test environments
9. **Ops** - Infrastructure patterns, deployment strategies, monitoring
10. **Version Control** - Git workflows, branching strategies, release management

Each agent has:
- **Dedicated keyword patterns** for content routing
- **Specialized memory sections** for organized knowledge storage
- **Configurable size limits** and learning preferences
- **Project-specific initialization** based on detected technology stack

## Architecture Deep Dive

### Service Layer

```
src/claude_mpm/services/
├── agent_memory_manager.py     # Core memory operations
│   ├── load_agent_memory()     # Load memory files with validation
│   ├── update_agent_memory()   # Add new learnings to sections
│   ├── optimize_memory()       # Remove duplicates and consolidate
│   └── get_memory_status()     # Comprehensive system status
│
├── memory_router.py            # Content routing and analysis
│   ├── analyze_and_route()     # Determine target agent for content
│   ├── get_supported_agents()  # List all supported agent types
│   └── test_routing_patterns() # Validate routing logic
│
├── memory_builder.py           # Documentation processing
│   ├── build_from_documentation()  # Extract insights from docs
│   ├── process_file()          # Individual file processing
│   └── route_to_agents()       # Distribute content to agents
│
├── memory_optimizer.py         # Memory maintenance
│   ├── optimize_agent_memory() # Single agent optimization
│   ├── remove_duplicates()     # Duplicate detection and removal
│   └── consolidate_similar()   # Merge related items
│
└── project_analyzer.py         # Project context analysis
    ├── analyze_project()       # Comprehensive project analysis
    ├── get_project_context_summary()  # Formatted summary
    └── get_important_files_for_context()  # Key files for processing
```

### Memory File Structure

```
.claude-mpm/memories/
├── engineer_agent.md           # Engineering patterns and implementations
├── research_agent.md           # Research findings and domain knowledge
├── qa_agent.md                # Quality standards and testing strategies
├── documentation_agent.md     # Writing standards and content organization
├── security_agent.md          # Security patterns and compliance
├── pm_agent.md                # Project coordination and processes
├── data_engineer_agent.md     # Data pipelines and analytics (New)
├── test_integration_agent.md  # Integration testing patterns (New)
├── ops_agent.md               # Infrastructure and deployment
├── version_control_agent.md   # Git workflows and versioning
├── .last_processed.json       # Documentation processing timestamps
└── README.md                  # Memory system overview
```

### Hook Integration

The memory system integrates with the Claude MPM hook system for seamless operation:

**PreDelegationHook (Priority: 20)**
```python
class MemoryPreDelegationHook(PreDelegationHook):
    def execute(self, context: HookContext) -> HookResult:
        agent_id = context.data.get('agent')
        memory_content = self.memory_manager.load_agent_memory(agent_id)
        context.data['agent_memory'] = memory_content
        return HookResult(success=True, modified=True, data=context.data)
```

**PostDelegationHook (Priority: 80)**
```python
class MemoryPostDelegationHook(PostDelegationHook):
    def execute(self, context: HookContext) -> HookResult:
        if self.auto_learning_enabled:
            agent_output = context.data.get('agent_output', '')
            extracted_learnings = self.extract_learnings(agent_output)
            for learning in extracted_learnings:
                self.memory_manager.add_learning(
                    learning['agent'], 
                    learning['type'], 
                    learning['content']
                )
        return HookResult(success=True, modified=False, data=context.data)
```

## Project Analysis Engine

### Technology Stack Detection

The `ProjectAnalyzer` automatically identifies:

**Configuration Files:**
- `package.json` → Node.js/JavaScript projects
- `requirements.txt`, `pyproject.toml` → Python projects
- `Cargo.toml` → Rust projects
- `pom.xml`, `build.gradle` → Java projects
- `composer.json` → PHP projects

**Framework Detection:**
```python
# Example detection logic
if 'react' in dependencies:
    characteristics.frameworks.append('React')
    characteristics.web_frameworks.append('React')
    
if 'django' in dependencies:
    characteristics.frameworks.append('Django')
    characteristics.web_frameworks.append('Django')
    
if 'express' in dependencies:
    characteristics.frameworks.append('Express')
    characteristics.web_frameworks.append('Express')
```

**Architecture Pattern Recognition:**
- SPA (Single Page Application) - React, Vue, Angular
- Web Service - Express, Django, Flask
- CLI Application - Click, Commander, Clap
- Desktop Application - Electron, Tauri, Qt

### Memory Template Generation

Based on analysis results, each agent receives tailored memory sections:

**Engineer Agent (React Project):**
```markdown
## Coding Patterns Learned
- Use functional components with hooks pattern
- Implement custom hooks for complex state logic
- Follow atomic design principles (atoms/molecules/organisms)
- Use React.memo for performance optimization where needed

## Implementation Guidelines
- TypeScript interfaces for all component props
- ESLint/Prettier configuration from .eslintrc.json
- API calls through axios service layer in src/services/
- State management with Redux Toolkit (configured in src/store/)
```

**QA Agent (React Project):**
```markdown
## Testing Strategies
- Component testing: @testing-library/react with user-event
- API mocking: MSW (Mock Service Worker) for integration tests
- E2E testing: Cypress with custom commands in cypress/support/
- Coverage requirements: 80% minimum, configured in jest.config.js
```

## CLI Interface Comprehensive Guide

### Memory Management Commands

**System Status and Health:**
```bash
# Comprehensive system overview
claude-mpm memory status

# Initialize project-specific memories
claude-mpm memory init

# Get raw JSON output for programmatic access
claude-mpm memory show --raw
```

**Viewing and Searching:**
```bash
# Show all agent memories (summary)
claude-mpm memory show

# Show specific agent with detailed format
claude-mpm memory show engineer --format detailed

# Search across all memories
claude-mpm memory cross-ref --query "testing patterns"

# Find common patterns across agents
claude-mpm memory cross-ref
```

**Adding and Managing Content:**
```bash
# Add learning to specific agent and section
claude-mpm memory add engineer pattern "Use dependency injection for services"
claude-mpm memory add qa error "Mock external APIs in integration tests"
claude-mpm memory add data_engineer optimization "Use connection pooling for database queries"

# Test content routing logic
claude-mpm memory route --content "Implement OAuth2 authentication"
```

**Maintenance and Optimization:**
```bash
# Optimize specific agent memory
claude-mpm memory optimize engineer

# Optimize all agent memories
claude-mpm memory optimize

# Build memories from project documentation
claude-mpm memory build

# Force rebuild all memories from documentation
claude-mpm memory build --force-rebuild
```

### Advanced Usage Patterns

**Batch Processing:**
```bash
#!/bin/bash
# Add multiple learnings for a new project setup
claude-mpm memory add engineer pattern "Use TypeScript strict mode configuration"
claude-mpm memory add engineer pattern "API routes follow RESTful conventions"
claude-mpm memory add qa context "Integration tests require Docker environment"
claude-mpm memory add qa pattern "Use data-testid attributes for E2E tests"
claude-mpm memory add ops context "Deploy to AWS ECS with Fargate"
```

**Memory Health Monitoring:**
```bash
# Monitor memory usage and get alerts
STATUS=$(claude-mpm memory status --raw)
HIGH_USAGE=$(echo $STATUS | jq '.agents | to_entries[] | select(.value.size_utilization > 90) | .key')

if [ ! -z "$HIGH_USAGE" ]; then
    echo "High memory usage detected for agents: $HIGH_USAGE"
    claude-mpm memory optimize
fi
```

## Advanced Configuration

### Production Configuration Example

```yaml
# .claude-mpm/config.yml
memory:
  enabled: true
  auto_learning: true
  
  limits:
    default_size_kb: 8
    max_sections: 10
    max_items_per_section: 15
    max_line_length: 120
  
  # Agent-specific optimizations
  agent_overrides:
    data_engineer:
      size_kb: 14                 # Larger for complex data patterns
      max_items_per_section: 20   # More items for pipeline patterns
      auto_learning: true
      
    test_integration:
      size_kb: 12                 # Medium size for test scenarios
      max_sections: 12            # More sections for different test types
      auto_learning: true
      
    research:
      size_kb: 16                 # Large for comprehensive findings
      auto_learning: true
      
    documentation:
      size_kb: 20                 # Largest for extensive documentation
      max_sections: 15
      auto_learning: true
  
  optimization:
    auto_optimize: true
    similarity_threshold: 0.85    # Balance between dedup and retention
    consolidation_threshold: 0.70 # Merge related items
  
  project_analysis:
    enabled: true
    cache_duration: 3600          # 1-hour cache for stability
    force_refresh_on_config_change: true
  
  documentation_processing:
    enabled: true
    file_patterns:
      - "README.md"
      - "CONTRIBUTING.md"
      - "docs/**/*.md"
      - "API.md"
      - "ARCHITECTURE.md"
    exclude_patterns:
      - "node_modules/**"
      - ".git/**"
      - "dist/**"
      - "build/**"
      - "coverage/**"

# Hook integration for seamless memory operation
hooks:
  memory_integration: true
  
  pre_delegation_hooks:
    - name: "memory_injection"
      enabled: true
      priority: 20
      
  post_delegation_hooks:
    - name: "memory_extraction"
      enabled: true
      priority: 80
```

## Performance Characteristics

### Memory File Size Guidelines

| Agent Type | Recommended Size | Max Items | Use Case |
|------------|------------------|-----------|----------|
| `engineer` | 8-12 KB | 80-120 | Code patterns, architecture |
| `research` | 12-16 KB | 100-150 | Analysis findings, domain knowledge |
| `qa` | 8-10 KB | 70-100 | Testing strategies, quality standards |
| `documentation` | 16-20 KB | 120-180 | Writing standards, content organization |
| `data_engineer` | 10-14 KB | 90-130 | Data pipelines, optimization patterns |
| `test_integration` | 8-12 KB | 80-120 | Integration patterns, E2E scenarios |
| `security` | 8-10 KB | 70-100 | Security patterns, compliance |
| `ops` | 10-12 KB | 80-120 | Infrastructure, deployment patterns |
| `pm` | 6-8 KB | 50-80 | Process, coordination patterns |
| `version_control` | 6-8 KB | 50-80 | Git workflows, release patterns |

### Optimization Impact

**Before Optimization:**
```
engineer: 12.3 KB, 156 items, 8 sections
- 23 duplicate items
- 15 highly similar items
- Sections in random order
```

**After Optimization:**
```
engineer: 9.7 KB, 118 items, 8 sections
- 0 duplicate items
- 3 consolidated items
- Priority-ordered sections
- 21% size reduction
```

## Integration Examples

### Custom Hook Integration

```python
from claude_mpm.hooks.base_hook import PreDelegationHook
from claude_mpm.services.agent_memory_manager import get_memory_manager

class ProjectContextHook(PreDelegationHook):
    def __init__(self):
        super().__init__(name="project_context", priority=15)
        self.memory_manager = get_memory_manager()
    
    def execute(self, context: HookContext) -> HookResult:
        agent_id = context.data.get('agent')
        task_type = context.data.get('task_type')
        
        # Load base memory
        agent_memory = self.memory_manager.load_agent_memory(agent_id)
        
        # Add task-specific context
        if task_type == 'api_development':
            api_patterns = self.extract_api_patterns(agent_memory)
            context.data['api_context'] = api_patterns
            
        elif task_type == 'data_processing':
            data_patterns = self.extract_data_patterns(agent_memory)
            context.data['data_context'] = data_patterns
        
        return HookResult(success=True, modified=True, data=context.data)
```

### API Integration

```python
from claude_mpm.services.agent_memory_manager import AgentMemoryManager
from claude_mpm.services.memory_router import MemoryRouter

class MemoryService:
    def __init__(self):
        self.memory_manager = AgentMemoryManager()
        self.router = MemoryRouter()
    
    def add_project_insight(self, content: str, context: dict = None):
        """Add insight with automatic agent routing."""
        routing = self.router.analyze_and_route(content, context)
        
        success = self.memory_manager.update_agent_memory(
            routing['target_agent'],
            routing['section'],
            content
        )
        
        return {
            'success': success,
            'agent': routing['target_agent'],
            'section': routing['section'],
            'confidence': routing['confidence']
        }
    
    def get_agent_expertise(self, agent_id: str) -> dict:
        """Get structured expertise summary for agent."""
        memory_content = self.memory_manager.load_agent_memory(agent_id)
        sections = self.memory_manager._parse_memory_content_to_dict(memory_content)
        
        return {
            'agent_id': agent_id,
            'expertise_areas': list(sections.keys()),
            'total_insights': sum(len(items) for items in sections.values()),
            'sections': sections
        }
```

## Troubleshooting Guide

### Common Issues and Solutions

**Memory System Not Learning:**
```bash
# Check system status
claude-mpm memory status

# Common causes:
# 1. Memory system disabled
memory:
  enabled: true  # Must be explicitly true

# 2. Auto-learning disabled
memory:
  auto_learning: true

# 3. Hooks not enabled
hooks:
  memory_integration: true
```

**Poor Routing Decisions:**
```bash
# Test routing with verbose output
claude-mpm memory route --content "your content here"

# Common solutions:
# 1. Add more specific keywords
# 2. Include context hints
# 3. Manual agent specification
```

**Memory Files Growing Too Large:**
```bash
# Check usage
claude-mpm memory status

# Solutions:
# 1. Run optimization
claude-mpm memory optimize

# 2. Reduce size limits
memory:
  limits:
    default_size_kb: 6

# 3. Enable auto-optimization
memory:
  optimization:
    auto_optimize: true
```

### Debug Logging

```bash
# Enable debug mode
export CLAUDE_MPM_LOG_LEVEL=DEBUG

# View detailed memory operations
claude-mpm memory status
claude-mpm memory add engineer test "debug content"
claude-mpm memory optimize
```

## Future Roadmap

### Planned Enhancements

**Semantic Search:**
- Vector embeddings for similarity matching
- Semantic deduplication beyond text matching
- Intelligent content consolidation

**Machine Learning Integration:**
- Usage pattern analysis
- Predictive memory sizing
- Automated optimization scheduling

**Enhanced Project Analysis:**
- Code pattern recognition via AST analysis
- Dependency relationship mapping
- Architecture pattern detection

**Multi-Project Memory Sharing:**
- Cross-project pattern recognition
- Shared knowledge repositories
- Team-wide memory synchronization

This comprehensive documentation provides complete coverage of the Claude MPM Agent Memory System, from basic usage to advanced integration patterns and troubleshooting guidance.