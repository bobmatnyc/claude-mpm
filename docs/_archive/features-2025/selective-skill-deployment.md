# Selective Skill Deployment

## Overview

Selective skill deployment automatically deploys only the skills referenced by your agents, reducing the number of deployed skills from ~78 to ~20 for typical projects. It also tracks deployed skills and automatically removes orphaned skills that are no longer referenced.

## Features

### 1. Agent-Based Skill Discovery

The system scans all deployed agents (`.claude/agents/*.md`) and extracts skill requirements from two sources:

**Source 1: Explicit Frontmatter Declarations**
```yaml
---
name: python-engineer
skills:
  - systematic-debugging
  - test-driven-development
---
```

Or using the required/optional format:
```yaml
---
name: python-engineer
skills:
  required:
    - systematic-debugging
  optional:
    - test-driven-development
---
```

**Source 2: Pattern-Based Inference (SkillToAgentMapper)**
The system automatically infers skills based on agent type, toolchain, and patterns. For example, a `python-engineer` agent automatically gets Python-related skills.

### 2. Deployment Tracking

All skills deployed by claude-mpm are tracked in `~/.claude/skills/.mpm-deployed-skills.json`:

```json
{
  "deployed_skills": {
    "systematic-debugging": {
      "collection": "claude-mpm-skills",
      "deployed_at": "2025-12-22T10:30:00Z"
    },
    "test-driven-development": {
      "collection": "claude-mpm-skills",
      "deployed_at": "2025-12-22T10:30:00Z"
    }
  },
  "last_sync": "2025-12-22T10:30:00Z"
}
```

### 3. Automatic Orphan Cleanup

When skills are deployed, the system automatically:
1. Identifies orphaned skills (tracked but no longer referenced by any agent)
2. Removes orphaned skill directories from `~/.claude/skills/`
3. Updates the tracking index

**Example:**
- Agent A had skills: `[skill-a, skill-b, skill-c]`
- Agent A updated to: `[skill-a, skill-c]`
- Next deployment: `skill-b` is automatically removed

### 4. Security Features

- **Path Traversal Protection**: Validates all skill paths before removal
- **Collection Tracking**: Records which collection each skill came from
- **Safe Cleanup**: Only removes skills tracked in the deployment index
- **Error Handling**: Gracefully handles permission errors and missing directories

## Usage

### Enable Selective Deployment (Default)

```bash
# Deploy skills (selective mode enabled by default)
claude-mpm skills deploy
```

### Disable Selective Deployment

```bash
# Deploy all skills in collection (no filtering)
claude-mpm skills deploy --no-selective
```

### Manual Cleanup

```python
from pathlib import Path
from claude_mpm.services.skills.selective_skill_deployer import (
    cleanup_orphan_skills,
    get_required_skills_from_agents
)

# Get required skills from agents
agents_dir = Path(".claude/agents")
required_skills = get_required_skills_from_agents(agents_dir)

# Clean up orphaned skills
claude_skills_dir = Path.home() / ".claude" / "skills"
result = cleanup_orphan_skills(claude_skills_dir, required_skills)

print(f"Removed {result['removed_count']} orphaned skills")
print(f"Kept {result['kept_count']} skills")
```

## API Reference

### `get_required_skills_from_agents(agents_dir: Path) -> Set[str]`

Extracts all skills referenced by deployed agents.

**Parameters:**
- `agents_dir`: Path to `.claude/agents/` directory

**Returns:**
- Set of unique skill names

**Example:**
```python
from pathlib import Path
from claude_mpm.services.skills.selective_skill_deployer import (
    get_required_skills_from_agents
)

agents_dir = Path(".claude/agents")
skills = get_required_skills_from_agents(agents_dir)
print(f"Found {len(skills)} required skills")
```

### `load_deployment_index(claude_skills_dir: Path) -> Dict[str, Any]`

Loads deployment tracking index.

**Returns:**
```python
{
    "deployed_skills": {
        "skill-name": {
            "collection": "collection-name",
            "deployed_at": "2025-12-22T10:30:00Z"
        }
    },
    "last_sync": "2025-12-22T10:30:00Z"
}
```

### `track_deployed_skill(claude_skills_dir: Path, skill_name: str, collection: str)`

Tracks a newly deployed skill.

**Parameters:**
- `claude_skills_dir`: Path to `~/.claude/skills/`
- `skill_name`: Name of deployed skill
- `collection`: Collection name

### `untrack_skill(claude_skills_dir: Path, skill_name: str)`

Removes skill from tracking index.

**Parameters:**
- `claude_skills_dir`: Path to `~/.claude/skills/`
- `skill_name`: Name of skill to untrack

### `cleanup_orphan_skills(claude_skills_dir: Path, required_skills: Set[str]) -> Dict[str, Any]`

Removes orphaned skills.

**Parameters:**
- `claude_skills_dir`: Path to `~/.claude/skills/`
- `required_skills`: Set of skill names that should remain deployed

**Returns:**
```python
{
    "removed_count": 2,
    "removed_skills": ["old-skill-1", "old-skill-2"],
    "kept_count": 18,
    "errors": []
}
```

## Integration with SkillsDeployerService

The `deploy_skills()` method integrates selective deployment automatically:

```python
from claude_mpm.services.skills_deployer import SkillsDeployerService

deployer = SkillsDeployerService()

# Deploy with selective mode (default)
result = deployer.deploy_skills(
    collection="claude-mpm-skills",
    selective=True  # Default
)

print(f"Deployed: {result['deployed_count']} skills")
print(f"Cleaned up: {result['cleanup']['removed_count']} orphaned skills")
```

**Return Value:**
```python
{
    "deployed_count": 20,
    "skipped_count": 5,
    "deployed_skills": ["skill-a", "skill-b", ...],
    "skipped_skills": ["skill-already-deployed", ...],
    "errors": [],
    "selective_mode": True,
    "total_available": 108,
    "cleanup": {
        "removed_count": 3,
        "removed_skills": ["old-skill-1", "old-skill-2", "old-skill-3"],
        "kept_count": 20,
        "errors": []
    },
    "restart_required": True,
    "restart_instructions": "..."
}
```

## Migration Guide

### From Manual Skill Management

Before:
```bash
# Deploy all skills
claude-mpm skills deploy

# Manually remove unused skills
claude-mpm skills remove skill-a skill-b skill-c
```

After:
```bash
# Deploy skills (automatically filters and cleans up)
claude-mpm skills deploy
```

### From Legacy Frontmatter Format

Before:
```yaml
---
skills:
  - skill-a
  - skill-b
  - skill-c
---
```

After (recommended):
```yaml
---
skills:
  required:
    - skill-a
    - skill-b
  optional:
    - skill-c
---
```

## Troubleshooting

### Skills Not Deploying

**Problem:** Expected skills aren't being deployed.

**Solution:**
1. Check agent frontmatter has `skills:` field
2. Verify skill names match exactly (case-sensitive)
3. Check deployment logs for filtering details
4. Try disabling selective mode: `claude-mpm skills deploy --no-selective`

### Orphaned Skills Not Removed

**Problem:** Old skills remain after removing from agent.

**Solution:**
1. Run deployment again: `claude-mpm skills deploy`
2. Check `.mpm-deployed-skills.json` for tracking status
3. Manually verify skill directories in `~/.claude/skills/`
4. Check logs for cleanup errors

### Path Traversal Errors

**Problem:** Errors about "Path traversal attempt detected"

**Solution:**
1. This is a security feature - skill paths are validated
2. Check `.mpm-deployed-skills.json` for corrupted entries
3. Remove corrupted entries and re-deploy
4. Report issue if persistent

## Performance Considerations

### Token Usage

Selective deployment reduces token usage in two ways:

1. **Fewer Skills Loaded**: Claude Code only loads ~20 skills instead of ~78
2. **Smaller Prompts**: Agent instructions reference fewer skills

### Deployment Time

- **Initial**: ~5-10 seconds (download + filter + deploy + cleanup)
- **Updates**: ~2-3 seconds (git pull + filter + deploy + cleanup)
- **Cleanup**: <1 second (typically removes 0-5 skills)

### Disk Space

- **Before**: ~78 skills × 50KB = ~3.9MB
- **After**: ~20 skills × 50KB = ~1MB
- **Savings**: ~2.9MB per project

## Architecture

### Deployment Flow

```
┌─────────────────────────────────────────────┐
│ 1. Scan .claude/agents/*.md                │
│    - Parse YAML frontmatter                 │
│    - Extract skills: field                  │
│    - Query SkillToAgentMapper               │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 2. Combine Skill Sources                   │
│    - Frontmatter skills                     │
│    - Inferred skills (SkillToAgentMapper)   │
│    - Normalize paths (/ → -)                │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 3. Filter Available Skills                 │
│    - Match skill names                      │
│    - Apply toolchain filters                │
│    - Apply category filters                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 4. Deploy Skills                            │
│    - Copy to ~/.claude/skills/              │
│    - Track in .mpm-deployed-skills.json     │
│    - Record collection and timestamp        │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│ 5. Cleanup Orphaned Skills                 │
│    - Load tracking index                    │
│    - Find orphaned (tracked - required)     │
│    - Remove directories                     │
│    - Update tracking index                  │
└─────────────────────────────────────────────┘
```

### File Structure

```
~/.claude/
├── skills/
│   ├── .mpm-deployed-skills.json     # Tracking index
│   ├── systematic-debugging/         # Deployed skill
│   ├── test-driven-development/      # Deployed skill
│   └── ...
└── agents/
    ├── python-engineer.md            # Agent with skills
    ├── typescript-engineer.md        # Agent with skills
    └── ...
```

## Related Documentation

- [Skills System Overview](../skills/README.md)
- [Agent Frontmatter Reference](../agents/frontmatter.md)
- [SkillToAgentMapper](../skills/skill-to-agent-mapper.md)
- [Deployment Tracking API](../api/deployment-tracking.md)

## Changelog

### v1.0.0 (2025-12-22)
- Initial implementation
- Dual-source skill discovery (frontmatter + mapper)
- Deployment tracking index
- Automatic orphan cleanup
- Path traversal protection
- Comprehensive test coverage (22 tests, 100% pass rate)
