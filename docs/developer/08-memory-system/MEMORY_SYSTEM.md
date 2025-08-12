# Memory System Documentation

> **Navigation**: [Developer Guide](../README.md) → [Memory System](./README.md) → **Memory System Guide**

## Overview

The Claude MPM Memory System enables persistent learning and knowledge accumulation across agent sessions, transforming generic AI assistants into project-aware specialists that understand your codebase, conventions, and patterns.

## Table of Contents

1. [Core Capabilities](#core-capabilities)
2. [Architecture](#architecture)
3. [Memory Routing](#memory-routing)
4. [Memory Building](#memory-building)
5. [Memory Optimization](#memory-optimization)
6. [Response Handling](#response-handling)
7. [CLI Operations](#cli-operations)
8. [Configuration](#configuration)
9. [Best Practices](#best-practices)

## Core Capabilities

### Key Features

- **10 Specialized Agent Types** with dedicated memory sections
- **Project-Specific Memory Generation** through automated analysis
- **Enhanced Routing Algorithm** with intelligent keyword matching
- **Dynamic Documentation Processing** with file discovery
- **Real-Time Learning Integration** via hook system
- **Comprehensive CLI Interface** for management

### Supported Agents

1. **Engineer** - Implementation patterns, coding standards
2. **Research** - Analysis findings, domain knowledge
3. **QA** - Testing strategies, quality standards
4. **Documentation** - Technical writing, content organization
5. **Security** - Security patterns, compliance requirements
6. **PM** - Project coordination, team communication
7. **Data Engineer** - Data pipelines, AI APIs, analytics
8. **Test Integration** - Integration testing, E2E validation
9. **Ops** - Infrastructure patterns, deployment strategies
10. **Version Control** - Git workflows, release management

## Architecture

### Service Layer Structure

```
src/claude_mpm/services/
├── agent_memory_manager.py     # Core memory operations
├── memory_router.py            # Content routing and analysis
├── memory_builder.py           # Documentation processing
├── memory_optimizer.py         # Memory maintenance
└── project_analyzer.py         # Project context analysis
```

### Memory Storage Structure

```
.claude-mpm/
└── memories/
    ├── engineer_agent.md
    ├── research_agent.md
    ├── qa_agent.md
    ├── documentation_agent.md
    ├── security_agent.md
    ├── pm_agent.md
    ├── data_engineer_agent.md
    ├── test_integration_agent.md
    ├── ops_agent.md
    └── version_control_agent.md
```

### Memory File Format

```markdown
# Engineer Agent Memory

Context-aware knowledge for implementation and development.

## Implementation Patterns

- **Pattern**: Repository pattern for data access
  *Context*: Used across all service layers
  *Example*: `UserRepository.findById()`
  
- **Pattern**: Async/await for all I/O operations
  *Context*: Performance optimization
  *Example*: `await database.query()`

## Architecture Decisions

- **Decision**: Microservices with event-driven communication
  *Rationale*: Scalability and loose coupling
  *Trade-offs*: Increased complexity vs flexibility
```

## Memory Routing

### Routing Algorithm

```python
def analyze_and_route(content: str, agent_hint: Optional[str] = None):
    """
    Enhanced routing with square root normalization.
    """
    scores = {}
    
    for agent_type, patterns in AGENT_ROUTING_PATTERNS.items():
        score = 0
        
        # Keyword matching with multi-word bonus
        for keyword in patterns['keywords']:
            if keyword.lower() in content_lower:
                bonus = 1.5 if ' ' in keyword else 1.0
                score += bonus
        
        # Square root normalization
        if score > 0:
            score = score / math.sqrt(len(patterns['keywords']))
        
        scores[agent_type] = score
    
    # Apply agent hint if provided
    if agent_hint and agent_hint in scores:
        scores[agent_hint] *= 1.5
    
    return max(scores, key=scores.get)
```

### Routing Patterns

```python
AGENT_ROUTING_PATTERNS = {
    'engineer': {
        'keywords': ['implement', 'code', 'function', 'class', 
                    'method', 'architecture', 'design pattern'],
        'file_patterns': ['*.py', '*.js', '*.ts', '*.java']
    },
    'qa': {
        'keywords': ['test', 'quality', 'validation', 'coverage',
                    'unit test', 'integration test', 'e2e test'],
        'file_patterns': ['test_*.py', '*.test.js', '*.spec.ts']
    },
    'security': {
        'keywords': ['security', 'vulnerability', 'authentication',
                    'authorization', 'encryption', 'OWASP'],
        'file_patterns': ['security.md', '*.security.yaml']
    }
}
```

## Memory Building

### Documentation Processing

```python
def build_from_documentation(
    docs_dir: str = "docs",
    output_dir: Optional[str] = None,
    max_items_per_section: int = 50
) -> Dict[str, Any]:
    """
    Process documentation and build agent memories.
    """
    # Discover documentation files
    doc_files = discover_documentation_files(docs_dir)
    
    # Process each file
    insights = {}
    for file_path in doc_files:
        file_insights = process_file(file_path)
        
        # Route to appropriate agents
        for insight in file_insights:
            agent = route_content(insight['content'])
            if agent not in insights:
                insights[agent] = []
            insights[agent].append(insight)
    
    # Generate memory files
    for agent, agent_insights in insights.items():
        generate_memory_file(agent, agent_insights, output_dir)
    
    return insights
```

### Project Analysis

```python
def analyze_project(project_path: str = ".") -> Dict[str, Any]:
    """
    Analyze project structure and generate initial memories.
    """
    analysis = {
        'technology_stack': detect_technology_stack(project_path),
        'architecture_patterns': detect_patterns(project_path),
        'testing_framework': detect_testing_framework(project_path),
        'documentation_structure': analyze_docs(project_path)
    }
    
    # Generate agent-specific insights
    memories = {}
    memories['engineer'] = extract_engineering_patterns(analysis)
    memories['qa'] = extract_testing_strategies(analysis)
    memories['security'] = extract_security_concerns(analysis)
    
    return memories
```

## Memory Optimization

### Optimization Process

```python
def optimize_memory(
    agent_type: str,
    similarity_threshold: float = 0.85,
    max_items_per_section: int = 100
) -> Dict[str, Any]:
    """
    Optimize agent memory by removing duplicates and consolidating.
    """
    # Load current memory
    memory = load_agent_memory(agent_type)
    
    # Remove exact duplicates
    memory = remove_duplicates(memory)
    
    # Consolidate similar items
    memory = consolidate_similar(memory, similarity_threshold)
    
    # Trim to size limits
    memory = enforce_size_limits(memory, max_items_per_section)
    
    # Save optimized memory
    save_agent_memory(agent_type, memory)
    
    return {
        'agent': agent_type,
        'original_items': original_count,
        'optimized_items': len(memory),
        'reduction': reduction_percentage
    }
```

### Duplicate Detection

```python
def detect_duplicates(items: List[str]) -> List[Tuple[str, str]]:
    """
    Find duplicate or highly similar items.
    """
    duplicates = []
    
    for i, item1 in enumerate(items):
        for j, item2 in enumerate(items[i+1:], i+1):
            similarity = calculate_similarity(item1, item2)
            if similarity > 0.85:
                duplicates.append((item1, item2, similarity))
    
    return duplicates
```

## Response Handling

### Memory Extraction from Responses

```python
def extract_memory_from_response(response: str) -> List[Dict]:
    """
    Extract memory directives from agent responses.
    """
    memories = []
    
    # Pattern: # Add To Memory:\nType: [type]\nContent: [content]\n#
    pattern = r'# Add To Memory:.*?Type: (\w+).*?Content: (.+?)\n#'
    
    for match in re.finditer(pattern, response, re.DOTALL):
        memory_type = match.group(1)
        content = match.group(2).strip()
        
        memories.append({
            'type': memory_type,
            'content': content,
            'timestamp': datetime.now().isoformat()
        })
    
    return memories
```

### Real-Time Learning

```python
def process_response_for_learning(response: str, agent_type: str):
    """
    Process agent response for memory updates.
    """
    # Extract memory directives
    memories = extract_memory_from_response(response)
    
    if memories:
        # Load current memory
        current_memory = load_agent_memory(agent_type)
        
        # Add new memories to appropriate sections
        for memory in memories:
            section = map_type_to_section(memory['type'])
            if section not in current_memory:
                current_memory[section] = []
            current_memory[section].append(memory['content'])
        
        # Save updated memory
        save_agent_memory(agent_type, current_memory)
```

## CLI Operations

### Memory Management Commands

```bash
# View memory status
./claude-mpm memory status

# Build memories from documentation
./claude-mpm memory build --docs ./docs --output .claude-mpm/memories

# Optimize specific agent memory
./claude-mpm memory optimize --agent engineer

# Optimize all memories
./claude-mpm memory optimize --all

# Route content to determine target agent
./claude-mpm memory route "implement authentication system"

# Clear specific agent memory
./claude-mpm memory clear --agent qa

# Export memories for backup
./claude-mpm memory export --output ./backup/memories

# Import memories from backup
./claude-mpm memory import --input ./backup/memories
```

### Status Command Output

```
Memory System Status
====================

Agent Memories:
- engineer_agent.md: 2048 items, 156KB, last updated: 2025-01-12 10:30:00
- qa_agent.md: 1536 items, 98KB, last updated: 2025-01-12 09:15:00
- security_agent.md: 892 items, 67KB, last updated: 2025-01-11 14:22:00

Total Memory Usage: 421KB / 10MB (4.2%)
Active Agents: 8 / 10
Optimization Recommended: qa_agent (duplicate ratio: 23%)
```

## Configuration

### Memory Configuration File

```yaml
# .claude-mpm/config/memory.yaml
memory:
  enabled: true
  auto_optimize: true
  optimization_threshold: 0.85
  max_items_per_section: 100
  max_memory_size_mb: 10
  
  agents:
    engineer:
      enabled: true
      max_items: 150
      sections:
        - implementation_patterns
        - architecture_decisions
        - code_standards
        - performance_optimizations
    
    qa:
      enabled: true
      max_items: 100
      sections:
        - test_strategies
        - quality_standards
        - bug_patterns
        - validation_rules
    
    security:
      enabled: true
      priority: high
      sections:
        - security_patterns
        - vulnerabilities
        - compliance_requirements
        - threat_models
  
  routing:
    confidence_threshold: 0.3
    multi_word_bonus: 1.5
    agent_hint_multiplier: 1.5
    use_file_patterns: true
```

### Environment Variables

```bash
# Memory system configuration
export CLAUDE_MPM_MEMORY_ENABLED=true
export CLAUDE_MPM_MEMORY_DIR=".claude-mpm/memories"
export CLAUDE_MPM_MEMORY_MAX_SIZE_MB=10
export CLAUDE_MPM_MEMORY_AUTO_OPTIMIZE=true
export CLAUDE_MPM_MEMORY_OPTIMIZATION_INTERVAL=86400  # Daily
```

## Best Practices

### 1. Memory Organization

- Keep memories focused and specific
- Use consistent formatting within sections
- Include context and examples
- Regular optimization to prevent bloat

### 2. Project Initialization

```bash
# Initialize memory for new project
./claude-mpm memory init

# Build from existing documentation
./claude-mpm memory build --docs ./docs

# Analyze project structure
./claude-mpm memory analyze --project .
```

### 3. Continuous Learning

- Enable response logging to capture learnings
- Review and curate memories periodically
- Use memory directives in agent instructions
- Monitor memory growth and optimize regularly

### 4. Team Collaboration

```bash
# Share memories with team
git add .claude-mpm/memories/
git commit -m "Update agent memories with latest learnings"

# Merge team memories
./claude-mpm memory merge --source teammate-memories/
```

### 5. Performance Optimization

- Set appropriate size limits per agent
- Use similarity thresholds to reduce duplicates
- Enable auto-optimization for large projects
- Monitor routing accuracy and adjust patterns

### 6. Security Considerations

- Don't store sensitive data in memories
- Review memories before committing to version control
- Use `.gitignore` for private memory files
- Sanitize memories when sharing publicly

## Troubleshooting

### Common Issues

1. **Memory Not Loading**
   ```bash
   # Check file permissions
   ls -la .claude-mpm/memories/
   
   # Validate memory format
   ./claude-mpm memory validate --agent engineer
   ```

2. **Routing Accuracy Issues**
   ```bash
   # Test routing patterns
   ./claude-mpm memory test-routing "your content here"
   
   # Adjust routing configuration
   vim .claude-mpm/config/memory.yaml
   ```

3. **Memory Bloat**
   ```bash
   # Check memory status
   ./claude-mpm memory status
   
   # Aggressive optimization
   ./claude-mpm memory optimize --all --threshold 0.7
   ```

4. **Duplicate Entries**
   ```bash
   # Detect duplicates
   ./claude-mpm memory analyze --duplicates
   
   # Remove duplicates
   ./claude-mpm memory optimize --agent engineer --remove-duplicates
   ```

## Advanced Features

### Custom Memory Sections

```python
# Define custom sections for specialized agents
CUSTOM_SECTIONS = {
    'ml_engineer': [
        'model_architectures',
        'training_strategies',
        'hyperparameter_tuning',
        'deployment_patterns'
    ],
    'devops': [
        'ci_cd_pipelines',
        'infrastructure_as_code',
        'monitoring_strategies',
        'incident_response'
    ]
}
```

### Memory Versioning

```bash
# Tag memory version
./claude-mpm memory tag --version v1.0.0

# Rollback to previous version
./claude-mpm memory rollback --version v0.9.0

# Compare memory versions
./claude-mpm memory diff --from v0.9.0 --to v1.0.0
```

### Cross-Project Memory Sharing

```bash
# Export memory template
./claude-mpm memory export-template --output template.json

# Import memory template
./claude-mpm memory import-template --input template.json

# Sync memories across projects
./claude-mpm memory sync --remote https://github.com/org/memories
```

## Related Documentation

- [Response System](../12-responses/README.md) - Response handling and logging
- [Response Logging](./response-logging.md) - Technical logging implementation
- [Memory Router](./router.md) - Content routing to appropriate agents
- [Memory Builder](./builder.md) - Building memories from documentation
- [Memory Optimizer](./optimizer.md) - Optimization and deduplication

## See Also

- [Main Memory Guide](../../MEMORY.md) - User-focused memory documentation
- [Agent Development](../07-agent-system/AGENT_DEVELOPMENT.md) - Creating memory-aware agents
- [Security Guide](../09-security/SECURITY.md) - Memory security considerations
