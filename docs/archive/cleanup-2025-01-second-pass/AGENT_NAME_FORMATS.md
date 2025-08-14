# Agent Name Format Guide (ARCHIVED - OUTDATED)

## Overview

**NOTE: This document contains outdated information. Agent names must now match the deployed agent YAML frontmatter names exactly.**

This document clarifies the agent name formats used in different contexts within the claude-mpm system and Claude Code.

## Important Note About Claude Code's Task Tool

**UPDATE: Claude Code's Task tool requires exact agent names as defined in the deployed agent YAML frontmatter.** The names are not simply lowercase versions but must match the `name:` field in each agent's YAML header.

## Agent Name Formats by Context

### 1. Task Tool (Claude Code) - STRICT FORMAT REQUIRED

When using the Task tool in Claude Code, you **MUST** use the exact lowercase format:

```python
# CORRECT - These will work:
Task(description="Analyze patterns", subagent_type="research")
Task(description="Implement feature", subagent_type="engineer")
Task(description="Run tests", subagent_type="qa")
Task(description="Update docs", subagent_type="documentation")
Task(description="Check security", subagent_type="security")
Task(description="Deploy app", subagent_type="ops")
Task(description="Manage versions", subagent_type="version_control")  # underscore
Task(description="Process data", subagent_type="data_engineer")      # underscore
Task(description="Coordinate work", subagent_type="pm")
Task(description="Integration test", subagent_type="test_integration") # underscore

# WRONG - These will be rejected by Claude Code:
Task(description="Analyze patterns", subagent_type="Research")        # ❌ Capitalized
Task(description="Implement feature", subagent_type="Engineer")       # ❌ Capitalized
Task(description="Run tests", subagent_type="QA")                    # ❌ Uppercase
Task(description="Manage versions", subagent_type="version-control")  # ❌ Hyphen instead of underscore
Task(description="Process data", subagent_type="data-engineer")       # ❌ Hyphen instead of underscore
```

### 2. TodoWrite Format - Capitalized Display Names

TodoWrite entries use capitalized, human-readable format for display:

```
[Research] Analyze the codebase patterns
[Engineer] Implement authentication system
[QA] Execute comprehensive test suite
[Documentation] Update API reference
[Security] Perform vulnerability assessment
[Ops] Configure deployment pipeline
[Version Control] Create release tags
[Data Engineer] Optimize database queries
[PM] Coordinate sprint planning
```

### 3. Internal Framework Normalization

The claude-mpm framework's `AgentNameNormalizer` can handle various input formats and normalize them:

- **Input variations accepted by the framework:**
  - "Research", "research", "RESEARCH" → normalized to "Research" (display) / "research" (task)
  - "Engineer", "engineer", "engineering", "dev" → normalized to "Engineer" / "engineer"
  - "QA", "qa", "Qa", "quality", "testing" → normalized to "QA" / "qa"
  - "Version Control", "version_control", "version-control" → normalized to "Version Control" / "version_control"

- **Agent loader accepts:**
  - Both capitalized and lowercase formats
  - Automatically normalizes to find the correct agent template

## Key Differences and Gotchas

### Claude Code vs Framework

| Context | Format Required | Example |
|---------|----------------|---------|
| Claude Code Task tool | Exact YAML frontmatter names | `subagent_type="research-agent"` |
| TodoWrite display | Capitalized with spaces | `[Research]` |
| Agent loader (internal) | Flexible, normalizes automatically | Both "Research" and "research" work |
| Hook tracking | Normalizes on capture | Converts any format for consistency |

### Common Errors

1. **Using capitalized names in Task tool:**
   ```python
   # This will fail in Claude Code:
   Task(description="...", subagent_type="Research")  # ❌
   
   # Use this instead:
   Task(description="...", subagent_type="research")  # ✅
   ```

2. **Using hyphens instead of underscores:**
   ```python
   # Wrong:
   Task(description="...", subagent_type="version-control")  # ❌
   Task(description="...", subagent_type="data-engineer")    # ❌
   
   # Correct:
   Task(description="...", subagent_type="version_control")  # ✅
   Task(description="...", subagent_type="data_engineer")    # ✅
   ```

## Available Agents

The following agents are available in the system:

| Agent Type | Task Tool Format | TodoWrite Format | Purpose |
|------------|-----------------|------------------|---------|
| Research | `research` | `[Research]` | Investigation and analysis |
| Engineer | `engineer` | `[Engineer]` | Code implementation |
| QA | `qa` | `[QA]` | Testing and quality assurance |
| Documentation | `documentation` | `[Documentation]` | Docs and guides |
| Security | `security` | `[Security]` | Security assessments |
| Ops | `ops` | `[Ops]` | Deployment and infrastructure |
| Version Control | `version_control` | `[Version Control]` | Git and versioning |
| Data Engineer | `data_engineer` | `[Data Engineer]` | Data processing |
| PM | `pm` | `[PM]` | Project management |
| Test Integration | `test_integration` | `[Test Integration]` | Integration testing |

## Recommendations

1. **Always use lowercase format for Task tool** to avoid Claude Code validation errors
2. **Use capitalized format for TodoWrite** for better readability
3. **The framework will normalize formats internally** for tracking and display
4. **Check error messages carefully** - if you see "Agent type 'X' not found", you're likely using the wrong format for Claude Code

## Testing

Run the test script to verify agent name handling:

```bash
python scripts/test_agent_name_formats.py
```

This will test:
- AgentNameNormalizer conversions
- Agent loader with different formats
- TodoWrite to Task format conversions