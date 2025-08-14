# Agent Memory System

Learn how Claude MPM agents remember and apply knowledge across sessions.

**Last Updated**: 2025-08-14  
**Version**: 3.8.2

## Overview

The Agent Memory System enables Claude MPM agents to learn and improve over time by storing project-specific knowledge, patterns, and insights in persistent memory files.

### Key Benefits

- **Continuity**: Agents remember insights across sessions
- **Context-Awareness**: Learn project-specific patterns and conventions  
- **Efficiency**: Reduce repetitive explanations
- **Quality**: Learn from mistakes and successful patterns

## Quick Start

### Initialize Project Memory
```bash
# Automatically analyze project and create memories
claude-mpm memory init
```

### Check Memory Status
```bash
# View current memory state
claude-mpm memory status
```

### Add Learning
```bash
# Add specific knowledge
claude-mpm memory add engineer pattern "Use src/ layout for Python packages"
```

## How Agents Learn

### Automatic Learning
- **Project Analysis**: Scans codebase for patterns and conventions
- **Documentation Extraction**: Learns from README, docs, comments
- **Technology Detection**: Identifies frameworks and tools in use
- **Architecture Recognition**: Understands project structure

### Manual Learning
- **Direct Commands**: `claude-mpm memory add [agent] [type] [content]`
- **Interactive Sessions**: Say "remember this" during conversations
- **File Editing**: Direct editing of memory files

### Memory Types

**Patterns**: Code patterns, architectural decisions, conventions
```bash
claude-mpm memory add engineer pattern "Always use async/await for database operations"
```

**Mistakes**: Common errors to avoid
```bash
claude-mpm memory add qa mistake "Don't forget to test error handling paths"
```

**Architecture**: System design and structure insights
```bash
claude-mpm memory add engineer architecture "Uses microservices with Docker containers"
```

**Context**: Project-specific information
```bash
claude-mpm memory add pm context "Team prefers TypeScript over JavaScript"
```

## Memory Commands

### Basic Operations
```bash
# Initialize memories
claude-mpm memory init

# Show status
claude-mpm memory status  

# List all memories
claude-mpm memory list

# Search memories
claude-mpm memory search "authentication"
```

### Adding Memories
```bash
# Add by type
claude-mpm memory add [agent] [type] [content]

# Examples
claude-mpm memory add engineer pattern "Use repository pattern for data access"
claude-mpm memory add qa guideline "Write integration tests for API endpoints"
claude-mpm memory add docs context "Documentation uses Sphinx with MyST parser"
```

### Managing Memories
```bash
# View specific agent memories
claude-mpm memory view engineer

# Clear all memories (with confirmation)
claude-mpm memory clear

# Optimize and compress memories
claude-mpm memory optimize
```

## Agent-Specific Memories

### Engineer Agent
- Code patterns and conventions
- Architecture decisions
- Technology preferences
- Development workflows

### QA Agent  
- Testing strategies
- Quality standards
- Common bug patterns
- Validation approaches

### Documentation Agent
- Documentation standards
- Writing style preferences
- Format requirements
- Structure patterns

### Research Agent
- Analysis techniques
- Investigation patterns
- Research methodologies
- Information sources

## Memory Storage

### Location
Memories are stored in `.claude-mpm/memory/` directory:
```
.claude-mpm/
└── memory/
    ├── engineer_memory.json
    ├── qa_memory.json  
    ├── docs_memory.json
    └── shared_memory.json
```

### Format
```json
{
  "agent_id": "engineer",
  "memories": [
    {
      "type": "pattern",
      "content": "Use dependency injection for loose coupling",
      "timestamp": "2025-08-14T10:30:00Z",
      "context": "Python web application architecture"
    }
  ]
}
```

## Best Practices

### Memory Management
- Initialize memories for each new project
- Add project-specific conventions early
- Review and curate memories periodically  
- Use descriptive, actionable memory content

### Effective Memory Content
- Be specific and actionable
- Include context when helpful
- Focus on patterns that repeat
- Document both successes and failures

### Examples of Good Memories
```bash
# Specific and actionable
claude-mpm memory add engineer pattern "Use Pydantic models for API validation"

# Includes context
claude-mpm memory add qa context "Integration tests use TestContainers for database"

# Learning from mistakes  
claude-mpm memory add ops mistake "Always check disk space before large deployments"
```

## Project-Specific Memory

### Technology Stack Detection
The system automatically identifies:
- Programming languages and versions
- Frameworks and libraries  
- Build tools and configuration
- Testing frameworks
- Documentation tools

### Architecture Recognition
- Directory structure patterns
- Module organization
- Design patterns in use
- Communication patterns

### Convention Learning
- Code style preferences
- Naming conventions
- File organization
- Documentation style

## Memory Integration

### During Sessions
Agents automatically reference relevant memories:
- Check patterns before implementing
- Apply learned conventions
- Avoid known mistakes
- Follow established guidelines

### Real-time Learning
- Extract insights from successful implementations
- Note patterns that work well
- Document decisions and rationale
- Update memories based on outcomes

## Troubleshooting

### Common Issues

**Memory Not Loading**
```bash
# Reinitialize
claude-mpm memory init --force

# Check status
claude-mpm memory status
```

**Corrupted Memory Files**
```bash
# Clear and reinitialize
claude-mpm memory clear
claude-mpm memory init
```

**Memory Search Not Working**
```bash
# Rebuild search index
claude-mpm memory optimize
```

### Memory File Issues
If memory files become corrupted, delete them and reinitialize:
```bash
rm -rf .claude-mpm/memory/
claude-mpm memory init
```

## Advanced Usage

### Memory Hooks
Integrate memory system with custom hooks for automatic learning extraction.

### Bulk Memory Import
```bash
# Import from JSON file
claude-mpm memory import memories.json

# Export current memories
claude-mpm memory export > project_memories.json
```

### Memory Sharing
Share project memories across team:
1. Export memories: `claude-mpm memory export`
2. Commit memory files to version control
3. Team members run: `claude-mpm memory import`

## Next Steps

- **Configuration**: [../reference/configuration.md](../reference/configuration.md)
- **Advanced Features**: [../developer/08-memory-system/](../../developer/08-memory-system/)
- **API Reference**: [../../developer/04-api-reference/](../../developer/04-api-reference/)

For comprehensive technical details, see the full [MEMORY.md](../MEMORY.md) documentation.