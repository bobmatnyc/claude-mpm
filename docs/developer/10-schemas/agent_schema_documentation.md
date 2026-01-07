# Agent Schema Documentation

Complete specification for agent frontmatter and structure.

## Agent Frontmatter Schema

### Required Fields

```yaml
---
name: string          # Unique identifier (kebab-case)
version: string       # Semantic version (MAJOR.MINOR.PATCH)
capabilities: array   # List of capabilities
---
```

### Optional Fields

```yaml
---
description: string   # Brief description
priority: number      # Selection priority (0-100, default 50)
tags: array          # Searchable tags
dependencies: array  # Required services or tools
---
```

### Complete Example

```yaml
---
name: python-engineer
version: 2.3.0
capabilities:
  - python-development
  - type-hints
  - async-programming
description: "Type-safe, async-first Python development with SOA patterns"
priority: 80
tags:
  - python
  - engineering
  - backend
dependencies:
  - python-3.8+
  - mypy
---
```

## Agent Structure

### Full Agent Template

```markdown
---
name: my-agent
version: 1.0.0
capabilities:
  - custom-capability
description: "Brief description of agent purpose"
priority: 50
---

# My Agent

## Role

What this agent does and its area of expertise.

## Capabilities

- Capability 1 description
- Capability 2 description
- Capability 3 description

## Workflow

1. Step 1
2. Step 2
3. Step 3

## Best Practices

- Practice 1
- Practice 2
- Practice 3

## Examples

Example usage and outputs.
```

## Capability Definitions

### Primary Capabilities

Core expertise areas:

- `orchestration` - PM/coordination capabilities
- `python-development` - Python programming
- `rust-development` - Rust programming
- `web-development` - Frontend/UI development
- `testing` - QA and testing
- `documentation` - Technical writing
- `security` - Security analysis
- `research` - Code analysis and research

### Secondary Capabilities

Supporting skills:

- `type-hints` - Python type annotations
- `async-programming` - Asynchronous code
- `api-design` - API architecture
- `database` - Database operations
- `deployment` - Ops and deployment
- `refactoring` - Code optimization

### Tool Capabilities

External tool integration:

- `git` - Version control
- `docker` - Containerization
- `kubernetes` - Orchestration
- `ci-cd` - Continuous integration
- `monitoring` - Observability

## Version Specification

### Semantic Versioning

Follow semver (MAJOR.MINOR.PATCH):

- **MAJOR**: Breaking changes to agent interface
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, documentation updates

### Version Examples

```yaml
version: 1.0.0   # Initial release
version: 1.1.0   # New feature added
version: 1.1.1   # Bug fix
version: 2.0.0   # Breaking change
```

## Priority System

Priority determines agent selection when multiple agents match:

- **90-100**: Critical specialists (high priority)
- **70-89**: Primary specialists
- **50-69**: General purpose (default)
- **30-49**: Supporting agents
- **0-29**: Fallback agents

### Priority Examples

```yaml
priority: 95   # Highly specialized (Python Engineer)
priority: 75   # Specialist (QA Agent)
priority: 50   # General (Documentation Agent)
priority: 30   # Supporting (Project Organizer)
```

## Validation

### Schema Validation

Agents are validated on load:

```bash
# Check agent validity
claude-mpm doctor --checks agents

# Validate specific agent
python -c "from claude_mpm.agents import AgentRegistry; AgentRegistry().load_agent('path/to/agent.md')"
```

### Common Validation Errors

**Missing Required Field:**
```
Error: Agent missing required field: name
```

**Invalid Version Format:**
```
Error: Invalid version format: "v1.0" (use "1.0.0")
```

**Empty Capabilities:**
```
Error: Agent must have at least one capability
```

## File Naming

### Agent Files

- Use kebab-case: `python-engineer.md`
- Match name field: `python-engineer.md` → `name: python-engineer`
- Place in appropriate tier:
  - System: Bundled with Claude MPM
  - User: `~/.claude-agents/`
  - Project: `.claude-mpm/agents/`

## Memory Schema

### Memory Response Format

Agents can update memory via JSON response:

```json
{
  "remember": [
    "Project uses FastAPI for backend",
    "Tests require pytest-asyncio",
    "Code style: Black with 100-char lines"
  ]
}
```

### Memory Replacement

Complete memory replacement:

```json
{
  "MEMORIES": [
    "Updated memory 1",
    "Updated memory 2",
    "Updated memory 3"
  ]
}
```

## See Also

- **[Creating Agents](../../agents/creating-agents.md)** - Step-by-step guide
- **[Agent Patterns](../../agents/agent-patterns.md)** - Design patterns
- **[Agent System](../../agents/README.md)** - Complete overview
- **[API Reference](../api-reference.md)** - API documentation

---

**For agent development**: See [../../agents/creating-agents.md](../../agents/creating-agents.md)
