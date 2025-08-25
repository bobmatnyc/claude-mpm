# User-Level Memory Support

## Overview

Claude MPM now supports **user-level memories** in addition to project-level memories. This allows users to maintain global knowledge and guidelines that apply across all their projects, while still having project-specific memories that can override or extend these defaults.

## Directory Structure

```
~/.claude-mpm/memories/          # User-level memories (global)
├── README.md                    # Documentation for user memories
├── PM.md                        # PM agent global memory
├── engineer_agent.md            # Engineer agent global memory
├── research_agent.md            # Research agent global memory
└── ...                          # Other agent memories

./.claude-mpm/memories/          # Project-level memories (local)
├── README.md                    # Documentation for project memories
├── PM.md                        # PM agent project memory
├── engineer_agent.md            # Engineer agent project memory
├── research_agent.md            # Research agent project memory
└── ...                          # Other agent memories
```

## How It Works

### Loading Order

1. **User memories are loaded first** from `~/.claude-mpm/memories/`
2. **Project memories are loaded second** from `./.claude-mpm/memories/`
3. **Memories are aggregated** with project memories taking precedence

### Aggregation Strategy

When both user and project memories exist for the same agent:

- **Sections are merged**: All sections from both sources are included
- **Duplicate items are removed**: Within each section, exact duplicates are eliminated
- **Project overrides user**: When conflicts exist, project-specific memories take precedence
- **Unique content is preserved**: All unique learnings from both sources are retained

### Example Aggregation

**User Memory** (`~/.claude-mpm/memories/engineer_agent.md`):
```markdown
## Implementation Guidelines
- Always use type hints in Python
- Follow SOLID principles
- Write comprehensive docstrings

## Common Mistakes to Avoid
- Avoid premature optimization
- Don't use global variables
```

**Project Memory** (`./.claude-mpm/memories/engineer_agent.md`):
```markdown
## Implementation Guidelines
- Use async/await for all database operations
- Follow FastAPI naming conventions
- Write comprehensive docstrings  # Duplicate - will be merged

## Project Architecture
- Microservices with REST APIs
- PostgreSQL database
```

**Aggregated Result** (what the agent sees):
```markdown
# Engineer Agent Memory
*Aggregated from user-level and project-level memories*

## Implementation Guidelines
- Always use type hints in Python
- Follow FastAPI naming conventions
- Follow SOLID principles
- Use async/await for all database operations
- Write comprehensive docstrings  # Only appears once

## Common Mistakes to Avoid
- Avoid premature optimization
- Don't use global variables

## Project Architecture
- Microservices with REST APIs
- PostgreSQL database
```

## Use Cases

### User-Level Memories (Global)

Perfect for storing:
- **Personal coding standards**: Your preferred style guidelines
- **Common patterns**: Design patterns you always use
- **Global best practices**: Security, performance, testing standards
- **Tool preferences**: Preferred libraries, frameworks, utilities
- **Personal reminders**: Common mistakes you want to avoid

### Project-Level Memories (Local)

Perfect for storing:
- **Project architecture**: Specific architectural decisions
- **API conventions**: Project-specific naming and structure
- **Database schema**: Current models and relationships
- **Integration points**: External services and APIs
- **Team guidelines**: Project-specific coding standards

## Managing Memories

### Creating User Memories

User memories are automatically created in `~/.claude-mpm/memories/` when:
1. The system initializes for the first time
2. An agent learns something marked as "global" or "universal"

You can also manually create or edit these files:
```bash
# Edit user-level engineer memory
vim ~/.claude-mpm/memories/engineer_agent.md
```

### Creating Project Memories

Project memories are created in `./.claude-mpm/memories/` when:
1. You initialize a project with `claude-mpm`
2. An agent learns something project-specific
3. You run memory-related commands

You can manually edit these as well:
```bash
# Edit project-level engineer memory
vim .claude-mpm/memories/engineer_agent.md
```

### Memory File Format

All memory files follow the same markdown format:
```markdown
# Agent Name Memory

## Section Name
- Learning item 1
- Learning item 2
- Learning item 3

## Another Section
- More learnings
```

## Benefits

1. **Reusable Knowledge**: Share common patterns across all projects
2. **Project Isolation**: Keep project-specific knowledge separate
3. **Override Capability**: Projects can override global defaults
4. **Reduced Repetition**: Don't need to teach agents the same things repeatedly
5. **Team Collaboration**: Share user memories with team members

## Technical Implementation

### Framework Loader Changes

The `FrameworkLoader` class now:
- Loads memories from both `~/.claude-mpm/memories/` and `./.claude-mpm/memories/`
- Aggregates memories using the `_aggregate_memories()` method
- Provides aggregated content to agents

### Agent Memory Manager Changes

The `AgentMemoryManager` service now:
- Maintains both `user_memories_dir` and `project_memories_dir`
- Loads and aggregates memories from both sources
- Saves new learnings to the appropriate directory (project by default)

### Initialization Changes

The `ProjectInitializer` now:
- Creates `~/.claude-mpm/memories/` during user directory initialization
- Ensures both directories exist with appropriate README files

## Backward Compatibility

This feature is **fully backward compatible**:
- Existing project memories continue to work unchanged
- If no user memories exist, the system works exactly as before
- The aggregation only happens when both sources exist

## Configuration

Future versions may support configuration options like:
- Disabling user memories for specific projects
- Changing the aggregation strategy
- Setting memory size limits per directory
- Controlling which agents use user memories

## Best Practices

1. **Keep user memories general**: Focus on universal principles and patterns
2. **Keep project memories specific**: Include project-specific details and context
3. **Review periodically**: Clean up outdated or incorrect memories
4. **Version control project memories**: Include `.claude-mpm/memories/` in git
5. **Share user memories**: Consider sharing useful patterns with your team