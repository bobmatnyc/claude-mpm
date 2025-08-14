# Agent Memory System

The Agent Memory System allows Claude MPM agents to learn and retain knowledge across sessions, improving performance over time.

**Last Updated**: 2025-08-14  
**Version**: 3.8.2

## Overview

### What is Agent Memory?

Agent Memory enables Claude MPM agents to:
- **Learn project patterns** and conventions
- **Remember insights** across sessions
- **Apply past knowledge** to new tasks
- **Improve quality** over time

### How It Works

1. **Automatic Learning**: Agents extract insights from your project structure, code, and documentation
2. **Persistent Storage**: Knowledge stored in `.claude-mpm/memory/` directory  
3. **Contextual Application**: Agents reference relevant memories when working
4. **Continuous Improvement**: Memories updated based on successful patterns

## Quick Start

### Initialize Project Memory
```bash
# Analyze project and create memories
claude-mpm memory init
```

This scans your project and creates agent-specific memories based on:
- Technology stack (languages, frameworks)
- Architecture patterns (directory structure, design patterns)
- Documentation and configuration files
- Existing code conventions

### Check Memory Status
```bash
# View current memory state
claude-mpm memory status
```

### Add Manual Learning
```bash
# Add specific knowledge
claude-mpm memory add engineer pattern "Use dependency injection for services"
claude-mpm memory add qa guideline "Always test error handling paths"
```

## Memory Types

### Patterns
Code patterns, architectural decisions, conventions
```bash
claude-mpm memory add engineer pattern "Use async/await for I/O operations"
```

### Guidelines
Development guidelines and best practices
```bash
claude-mpm memory add qa guideline "Integration tests use TestContainers"
```

### Context
Project-specific information and preferences
```bash
claude-mpm memory add pm context "Team prefers TypeScript over JavaScript"
```

### Mistakes
Common errors to avoid
```bash
claude-mpm memory add engineer mistake "Don't forget to handle connection timeouts"
```

### Architecture
System design and structure insights
```bash
claude-mpm memory add engineer architecture "Microservices communicate via REST APIs"
```

## Memory Storage

Memories are stored in `.claude-mpm/memory/`:

```
.claude-mpm/memory/
├── engineer_memory.json
├── qa_memory.json
├── research_memory.json
├── documentation_memory.json
└── shared_memory.json
```

## Essential Commands

### View Memories
```bash
# List all memories
claude-mpm memory list

# View specific agent memories
claude-mpm memory view engineer

# Search memories
claude-mpm memory search "authentication"
```

### Manage Memories
```bash
# Optimize and clean up memories
claude-mpm memory optimize

# Clear all memories (with confirmation)
claude-mpm memory clear

# Export memories
claude-mpm memory export > project_memories.json

# Import memories
claude-mpm memory import project_memories.json
```

## Automatic Learning

### Project Analysis
When you run `claude-mpm memory init`, the system automatically:

1. **Detects Technology Stack**:
   - Programming languages and versions
   - Frameworks and libraries
   - Build tools and configuration

2. **Analyzes Architecture**:
   - Directory structure patterns
   - Module organization
   - Design patterns in use

3. **Extracts Conventions**:
   - Code style preferences
   - Naming conventions
   - File organization patterns

### Interactive Learning
During conversations, agents learn when you:
- Say "remember this for next time"
- Use phrases like "memorize this pattern"
- Ask agents to "learn from this mistake"

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

### Research Agent
- Analysis techniques
- Investigation patterns
- Information sources
- Research methodologies

### Documentation Agent
- Documentation standards
- Writing style preferences
- Format requirements
- Structure patterns

## Memory Integration

### During Tasks
Agents automatically:
- Check relevant memories before acting
- Apply learned patterns and conventions
- Avoid known mistakes
- Follow established guidelines

### Real-Time Learning
- Extract insights from successful implementations
- Note patterns that work well
- Document decisions and rationale
- Update memories based on outcomes

## Best Practices

### Memory Management
1. **Initialize early**: Run `claude-mpm memory init` for new projects
2. **Be specific**: Add concrete, actionable memories
3. **Include context**: Provide relevant background information
4. **Review regularly**: Use `claude-mpm memory optimize` periodically

### Effective Memory Content
```bash
# Good - specific and actionable
claude-mpm memory add engineer pattern "Use Pydantic for API request validation"

# Better - includes context  
claude-mpm memory add qa context "Integration tests run against staging database"

# Best - learning from experience
claude-mpm memory add ops mistake "Always verify disk space before large deployments"
```

## Common Issues

### Memory Not Loading
```bash
# Reinitialize memories
claude-mpm memory init --force

# Check status
claude-mpm memory status
```

### Corrupted Memory Files
```bash
# Clear and rebuild
claude-mpm memory clear
claude-mpm memory init
```

### Search Not Working
```bash
# Rebuild index
claude-mpm memory optimize
```

## Team Collaboration

### Sharing Memories
1. Export project memories:
   ```bash
   claude-mpm memory export > team_memories.json
   ```

2. Commit to version control:
   ```bash
   git add .claude-mpm/memory/
   git commit -m "Add project memory configuration"
   ```

3. Team members import:
   ```bash
   claude-mpm memory import team_memories.json
   ```

## Configuration

Memory system can be configured in `.claude-mpm/config.yaml`:

```yaml
memory:
  enabled: true
  max_memories_per_agent: 100
  auto_optimize: true
  learning_threshold: 0.8
```

## Next Steps

- **Basic Usage**: [basic-usage.md](user/basic-usage.md)
- **Advanced Configuration**: [user/reference/configuration.md](user/reference/configuration.md)
- **Technical Details**: [developer/08-memory-system/](developer/08-memory-system/)
- **API Reference**: [developer/04-api-reference/](developer/04-api-reference/)

For comprehensive technical documentation, see [developer/08-memory-system/MEMORY_SYSTEM.md](developer/08-memory-system/MEMORY_SYSTEM.md).