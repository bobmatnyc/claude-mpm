# Hierarchical BASE-AGENT.md Template Inheritance

## Overview

Claude MPM now supports hierarchical organization of agent templates using `BASE-AGENT.md` files. This allows agent repositories to define shared content at multiple levels of the directory tree, promoting code reuse and consistent standards across related agents.

## Feature Description

When deploying an agent, Claude MPM automatically discovers and composes `BASE-AGENT.md` files from the agent's directory hierarchy, walking up from the agent file to the repository root.

**Composition Order** (closest to farthest):
1. Agent-specific content (the `.md` file itself)
2. Local `BASE-AGENT.md` (same directory as agent)
3. Parent `BASE-AGENT.md` (parent directory)
4. Grandparent `BASE-AGENT.md` (grandparent directory)
... continuing to repository root

## Directory Structure Example

```
Git Repository:
engineering/
  BASE-AGENT.md           # Shared engineering principles
  python/
    BASE-AGENT.md         # Python-specific guidelines
    backend/
      fastapi-engineer.md # Specific agent
      django-engineer.md  # Specific agent
  javascript/
    BASE-AGENT.md         # JavaScript-specific guidelines
    react-engineer.md     # Specific agent
```

## Composition Result

**For `fastapi-engineer` deployment:**
```
Content =
  fastapi-engineer.md content
  + engineering/python/BASE-AGENT.md content
  + engineering/BASE-AGENT.md content
```

**For `react-engineer` deployment:**
```
Content =
  react-engineer.md content
  + engineering/javascript/BASE-AGENT.md content
  + engineering/BASE-AGENT.md content
```

## Example BASE-AGENT.md Files

### Root Level: `BASE-AGENT.md`

```markdown
# Company-Wide Agent Standards

## Core Values
- Customer first
- Quality over speed
- Continuous improvement

## Communication Style
- Clear and concise
- Professional tone
- Explain technical decisions
```

### Engineering Level: `engineering/BASE-AGENT.md`

```markdown
# Engineering Agent Principles

## Code Quality Standards
- Follow SOLID principles
- Write comprehensive tests
- Document complex logic

## Development Workflow
- Create feature branches
- Write meaningful commit messages
- Request code reviews
```

### Python Level: `engineering/python/BASE-AGENT.md`

```markdown
# Python-Specific Guidelines

## Code Style
- Follow PEP 8
- Use type hints
- Write docstrings for public APIs

## Best Practices
- Use virtual environments
- Pin dependencies in requirements.txt
- Prefer composition over inheritance
```

### Agent Level: `engineering/python/backend/fastapi-engineer.md`

```json
{
  "name": "fastapi-engineer",
  "description": "FastAPI backend development specialist",
  "agent_type": "engineer",
  "instructions": "# FastAPI Engineer\n\nExpert in building async REST APIs with FastAPI.\n\n## Specialization\n- Async/await patterns\n- Pydantic models\n- Dependency injection\n- OpenAPI documentation"
}
```

## Deployed Agent Content

When `fastapi-engineer` is deployed, the final content will be:

```markdown
---
name: fastapi-engineer
description: "FastAPI backend development specialist..."
model: sonnet
type: engineer
version: "1.0.0"
---

# FastAPI Engineer

Expert in building async REST APIs with FastAPI.

## Specialization
- Async/await patterns
- Pydantic models
- Dependency injection
- OpenAPI documentation

---

# Python-Specific Guidelines

## Code Style
- Follow PEP 8
- Use type hints
- Write docstrings for public APIs

## Best Practices
- Use virtual environments
- Pin dependencies in requirements.txt
- Prefer composition over inheritance

---

# Engineering Agent Principles

## Code Quality Standards
- Follow SOLID principles
- Write comprehensive tests
- Document complex logic

## Development Workflow
- Create feature branches
- Write meaningful commit messages
- Request code reviews

---

# Company-Wide Agent Standards

## Core Values
- Customer first
- Quality over speed
- Continuous improvement

## Communication Style
- Clear and concise
- Professional tone
- Explain technical decisions
```

## Use Cases

### 1. Multi-Language Engineering Organization

```
engineering/
  BASE-AGENT.md              # Engineering principles
  python/
    BASE-AGENT.md            # Python standards
    backend-engineer.md
    ml-engineer.md
  javascript/
    BASE-AGENT.md            # JavaScript standards
    frontend-engineer.md
    nodejs-engineer.md
  rust/
    BASE-AGENT.md            # Rust standards
    systems-engineer.md
```

### 2. Multi-Team Company Structure

```
company/
  BASE-AGENT.md              # Company-wide values
  product-team/
    BASE-AGENT.md            # Product team practices
    product-manager.md
    ux-designer.md
  engineering-team/
    BASE-AGENT.md            # Engineering practices
    backend-engineer.md
    devops-engineer.md
```

### 3. Progressive Enhancement

```
agents/
  BASE-AGENT.md              # Basic agent behavior
  specialized/
    BASE-AGENT.md            # Specialized agent additions
    domain-experts/
      BASE-AGENT.md          # Domain expert enhancements
      healthcare-expert.md
      finance-expert.md
```

## Implementation Details

### Discovery Algorithm

1. Start at agent file's directory
2. Check for `BASE-AGENT.md` in current directory
3. If found, add to composition list
4. Move to parent directory
5. Repeat until:
   - Reach `.git` directory (repository root)
   - Reach known repository root indicators (`.claude-mpm`, `remote-agents`, `cache`)
   - Reach filesystem root
   - Reach depth limit (10 levels for safety)

### Composition Algorithm

1. Read agent-specific content from `.md` file
2. Discover all `BASE-AGENT.md` files in hierarchy
3. Append each BASE template in order (closest to farthest)
4. Join sections with `---` separator
5. Add YAML frontmatter at the top

### Backward Compatibility

The system maintains backward compatibility with the legacy `BASE_{TYPE}.md` pattern:

- If NO `BASE-AGENT.md` files are found in hierarchy
- AND agent has an `agent_type` field
- THEN fall back to loading `BASE_{TYPE}.md` (e.g., `BASE_ENGINEER.md`)

This ensures existing agent repositories continue to work without modification.

## Benefits

### Code Reuse
Share common instructions across related agents without duplication.

### Organizational Hierarchy
Mirror your team structure in agent organization:
- Company standards at root
- Department standards in subdirectories
- Team standards in nested directories
- Individual agent specializations in leaf files

### Maintainability
Update shared content in one place, automatically propagated to all child agents.

### Gradual Adoption
Start with flat structure, add BASE templates incrementally as patterns emerge.

### Clear Separation of Concerns
- Root: Company-wide values and communication style
- Department: Domain-specific practices and standards
- Team: Technology-specific guidelines
- Agent: Individual specialization and expertise

## Best Practices

### 1. Keep BASE Templates Focused

Each BASE template should address concerns at its level:

```markdown
# ❌ BAD: Root BASE with Python-specific content
# Company Standards
- Use type hints (Python-specific, belongs in python/BASE-AGENT.md)
- Customer first (Good, company-wide)

# ✅ GOOD: Root BASE with universal content
# Company Standards
- Customer first
- Quality over speed
- Clear communication
```

### 2. Avoid Duplication

Don't repeat content that exists in parent templates:

```markdown
# ❌ BAD: Repeating parent content
# engineering/python/BASE-AGENT.md
- Follow SOLID principles (Already in engineering/BASE-AGENT.md)
- Use type hints (Good, Python-specific)

# ✅ GOOD: Only add new content
# engineering/python/BASE-AGENT.md
- Use type hints
- Follow PEP 8
- Write docstrings
```

### 3. Use Progressive Enhancement

Each level should enhance, not replace, parent content:

```markdown
# Root: Basic behavior
# Company Standards
- Be helpful and professional

# Department: Add context
# Engineering Standards
- Follow coding best practices
- Write tests

# Team: Add specifics
# Python Guidelines
- Use type hints
- Follow PEP 8
```

### 4. Test Composition

Before deploying, verify composition order is correct:

```bash
# Deploy a test agent
claude-mpm agents deploy fastapi-engineer --force

# Check deployed content
cat ~/.claude/agents/fastapi-engineer.md

# Verify sections appear in correct order:
# 1. Agent-specific
# 2. Local BASE
# 3. Parent BASE
# 4. Root BASE
```

## Migration Guide

### From Flat Structure

**Before:**
```
agents/
  fastapi-engineer.md    (contains all content)
  django-engineer.md     (duplicates common content)
  react-engineer.md      (duplicates common content)
```

**After:**
```
agents/
  BASE-AGENT.md          (shared content)
  python/
    BASE-AGENT.md        (Python shared content)
    fastapi-engineer.md  (specific content only)
    django-engineer.md   (specific content only)
  javascript/
    BASE-AGENT.md        (JavaScript shared content)
    react-engineer.md    (specific content only)
```

### Migration Steps

1. **Identify Common Content**
   - Review all agents in category
   - Extract shared instructions
   - Identify hierarchy levels

2. **Create BASE Templates**
   - Create root `BASE-AGENT.md` with universal content
   - Create subdirectory `BASE-AGENT.md` files for category content
   - Keep agent files with specific content only

3. **Test Composition**
   - Deploy agents with `--force` flag
   - Verify composed content is correct
   - Check that no content was lost

4. **Clean Up**
   - Remove duplicated content from agent files
   - Update documentation
   - Commit changes to repository

## Troubleshooting

### BASE Template Not Found

**Symptom:** Expected BASE content missing from deployed agent

**Solutions:**
- Verify `BASE-AGENT.md` file exists in expected directory
- Check file permissions (must be readable)
- Ensure file is named exactly `BASE-AGENT.md` (case-sensitive)
- Redeploy with `--force` flag

### Wrong Composition Order

**Symptom:** Sections appear in unexpected order

**Explanation:** Composition order is always:
1. Agent-specific (closest)
2. Local BASE (same directory)
3. Parent BASE (parent directory)
... to root (farthest)

**Fix:** Move content to appropriate BASE template level

### Encoding Errors

**Symptom:** Deployment fails with Unicode/encoding errors

**Solutions:**
- Ensure all `.md` files are UTF-8 encoded
- Check for invalid characters
- Verify file is plain text, not binary

### Depth Limit Reached

**Symptom:** Warning about depth limit in logs

**Explanation:** Safety limit of 10 directory levels prevents infinite loops

**Solutions:**
- Flatten directory structure
- Move agents closer to repository root
- Report issue if legitimate deep structure needed

## Technical Reference

### File Naming

- **Required:** `BASE-AGENT.md` (exact case)
- **Location:** Any directory in hierarchy
- **Format:** Markdown (`.md` extension)
- **Encoding:** UTF-8

### Discovery Rules

1. Start at agent file's parent directory
2. Search for `BASE-AGENT.md` in current directory
3. Move to parent and repeat
4. Stop at:
   - `.git` directory (repository root)
   - `.claude-mpm`, `remote-agents`, `cache` (known roots)
   - Filesystem root
   - 10 directory levels (safety limit)

### Composition Format

```
YAML Frontmatter
---
Agent-Specific Content
---
Local BASE-AGENT.md Content
---
Parent BASE-AGENT.md Content
---
Grandparent BASE-AGENT.md Content
```

Sections are joined with `---` separator (three hyphens).

## Related Features

- **Agent Deployment**: Core deployment system that uses composition
- **Git Agent Sources**: Remote agent repositories can use hierarchical structure
- **Agent Templates**: JSON templates are composed with BASE content
- **Multi-Source Deployment**: Highest version wins across all sources

## Future Enhancements

Potential improvements for future releases:

1. **Conditional Composition**
   - Include/exclude BASE templates based on agent metadata
   - Environment-specific BASE templates (dev/staging/prod)

2. **BASE Template Validation**
   - Lint BASE templates for common issues
   - Validate composition order
   - Detect circular references

3. **Composition Visualization**
   - CLI command to show composition tree
   - Show which BASE templates will be included
   - Preview final composed content

4. **BASE Template Versioning**
   - Version BASE templates independently
   - Track which agents use which BASE versions
   - Migrate agents when BASE templates update

## See Also

- [Agent Deployment Guide](../user/agent-deployment.md)
- [Agent Template Format](../reference/agent-template-format.md)
- [Git Agent Sources](../features/agent-sources.md)
- [Agent Development Best Practices](../development/agent-best-practices.md)
