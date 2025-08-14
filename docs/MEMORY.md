# Agent Memory System

The Agent Memory System enables agents to learn and apply project-specific knowledge over time, creating persistent learnings that improve agent effectiveness across sessions.

Last Updated: 2025-08-14

## Overview

### What is the Memory System?

The memory system allows agents to accumulate project-specific knowledge, patterns, and learnings in persistent memory files. When agents encounter situations they've learned from before, they can apply that knowledge to make better decisions and provide more contextually relevant assistance.

### Why is it Important?

- **Continuity**: Agents remember insights across sessions, building expertise over time
- **Context-Awareness**: Agents learn project-specific patterns, conventions, and requirements
- **Efficiency**: Reduces repetitive explanations and accelerates problem-solving
- **Quality**: Agents learn from mistakes and successful patterns to improve output quality

### How Agents Learn

Agents accumulate knowledge through:
1. **Explicit Memory Commands**: Users say "remember this" or "add to memory"
2. **Auto-Learning**: Automatic extraction from agent outputs (when enabled)
3. **Project-Specific Memory Generation**: Automated analysis of project characteristics
4. **Manual Addition**: Direct memory file editing or CLI commands

## Quick Start

### Initialize Project Memory

```bash
# Automatically analyze project and create tailored memories
claude-mpm memory init

# View memory status
claude-mpm memory status

# View specific agent's memory
claude-mpm memory show engineer
```

### Add Learning Manually

```bash
# Add pattern to engineer's memory
claude-mpm memory add engineer pattern "Always use async/await for I/O operations"

# Add mistake to avoid
claude-mpm memory add engineer mistake "Don't place test files outside /tests/ directory"
```

### Natural Language Memory

Agents recognize these phrases in conversation:
- "Remember this for next time"
- "Add this to memory"
- "Learn from this mistake"
- "Store this insight"

## Core Features

### Project-Specific Memory Generation

The memory system automatically analyzes your project to create context-aware memories tailored to your specific codebase, technology stack, and architecture patterns.

**Key Capabilities:**
- **Technology Stack Detection**: Automatically identifies languages, frameworks, and tools
- **Architecture Pattern Recognition**: Analyzes directory structure and code patterns
- **Dynamic File Discovery**: Finds important documentation and configuration files
- **Agent-Specific Customization**: Generates different content based on agent roles

**Example Analysis:**
```
claude-mpm: Python CLI Application
- Main modules: cli, services, core, utils
- Uses: click, pytest, flask
- Testing: pytest fixtures
- Key patterns: Object Oriented, Async Programming
```

### Memory Storage

Agents store memories in structured markdown files in `.claude-mpm/memories/`:

```
.claude-mpm/memories/
├── engineer_agent.md
├── research_agent.md  
├── qa_agent.md
└── documentation_agent.md
```

Each memory file contains sections for:
- **Project Architecture**: Project-specific patterns and conventions
- **Implementation Guidelines**: Coding standards and best practices
- **Common Mistakes**: Issues to avoid based on past experience
- **Useful Patterns**: Successful approaches and templates

### Memory Management

```bash
# View all agent memories
claude-mpm memory list

# Optimize memory files (remove duplicates, consolidate)
claude-mpm memory optimize

# Clear specific agent memory
claude-mpm memory clear engineer

# Export memories for backup
claude-mpm memory export --output memories-backup.json
```

## Configuration

### Basic Configuration

Memory system settings in `.claude-mpm/config.yaml`:

```yaml
memory:
  enabled: true
  max_size_kb: 8
  auto_learn: true
  backup_enabled: true
  
  # Agent-specific overrides
  agent_overrides:
    engineer:
      max_size_kb: 16
    research:
      auto_learn: false
```

### Advanced Options

```yaml
memory:
  # Memory optimization settings
  optimization:
    auto_optimize: true
    duplicate_threshold: 0.8
    
  # Project analysis settings
  analysis:
    scan_depth: 3
    include_patterns: ["*.py", "*.js", "*.md"]
    exclude_dirs: ["node_modules", "__pycache__"]
```

## Memory Format

Memory files follow a structured markdown format:

```markdown
# Agent Memory: Engineer

## Project Architecture
- Use src/ layout pattern for Python packages
- Follow service-oriented architecture with clear separation
- Store all scripts in /scripts/, never in project root

## Implementation Guidelines  
- All imports use full package name: from claude_mpm.module import ...
- Run E2E tests after significant changes
- Create backups before major optimizations

## Common Mistakes to Avoid
- Don't place test files outside of /tests/ directory
- Never update git config in automated scripts

## Useful Patterns
- Use dependency injection for service classes
- Implement caching for expensive operations
```

## Best Practices

### For Users

1. **Initialize Early**: Run `claude-mpm memory init` when starting work on a new project
2. **Review Regularly**: Use `claude-mpm memory show` to see what agents have learned
3. **Give Feedback**: When agents make mistakes, explicitly tell them to "remember this"
4. **Keep Clean**: Run `claude-mpm memory optimize` periodically to remove duplicates

### For Teams

1. **Share Memories**: Export and share memory files across team members
2. **Project Standards**: Use memory to enforce consistent coding standards
3. **Onboarding**: New team members benefit from accumulated project knowledge
4. **Documentation**: Memory complements traditional documentation with learned patterns

## Troubleshooting

### Common Issues

**Memory not persisting:**
```bash
# Check memory directory exists
ls -la .claude-mpm/memories/

# Verify memory system is enabled
claude-mpm memory status
```

**Project analysis incomplete:**
```bash
# Force refresh project analysis
claude-mpm memory init --force-refresh

# Check what was detected
claude-mpm memory status --verbose
```

**Memory files too large:**
```bash
# Optimize to reduce size
claude-mpm memory optimize

# Check current sizes
claude-mpm memory list --sizes
```

**Generic memories despite project-specific setup:**
```bash
# Rebuild with fresh analysis
claude-mpm memory init --rebuild

# Verify project context detection
claude-mpm memory show --project-context
```

### Getting Help

For detailed configuration options and advanced usage:
- [Developer Memory Guide](docs/developer/08-memory-system/README.md)
- [Memory System API](docs/api/modules.rst#memory-services)
- [Configuration Reference](docs/developer/08-memory-system/MEMORY_SYSTEM.md)

For issues and feature requests:
- [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- [Troubleshooting Guide](docs/user/troubleshooting.md)