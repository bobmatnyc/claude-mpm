# Orphaned Agent Cleanup Feature

## Overview

The orphaned agent cleanup feature automatically removes claude-mpm managed agents that are no longer deployed, while preserving user-created agents. This ensures `.claude/agents/` stays clean and only contains currently configured agents.

## Problem Solved

When agent configurations change (e.g., agents removed from `agents.yml` or remote sources), old agent files would remain in `.claude/agents/`, leading to:

- Confusion about which agents are active
- Stale agent references
- Cluttered agent directory
- Risk of using deprecated agents

## Solution

After successful agent deployment on startup, the system:

1. Identifies agents that SHOULD be deployed (from deployment result)
2. Scans `.claude/agents/` for all `.md` files
3. Checks each file's YAML frontmatter for ownership indicators
4. Removes files marked as "ours" but not in the current deployment set
5. Preserves user-created agents without ownership markers

## Ownership Detection

An agent is considered "ours" (managed by claude-mpm) if its YAML frontmatter contains ANY of:

- `author: Claude MPM Team` (or contains "Claude MPM")
- `source: remote`
- `agent_id: <any-value>` (indicates it's from our repo)

Example claude-mpm managed agent frontmatter:

```yaml
---
agent_id: python-engineer
author: Claude MPM Team
source: remote
version: 1.0.0
---
```

## User Agent Preservation

User-created agents are NEVER removed if they:

- Have no YAML frontmatter
- Have frontmatter without any ownership markers
- Are hidden files (start with `.`)
- Cannot be parsed (safety first)

Example user agent (preserved):

```yaml
---
name: My Custom Agent
version: 1.0.0
author: John Doe
---
```

## Implementation

### Location

`src/claude_mpm/cli/startup.py`

### Key Function

```python
def _cleanup_orphaned_agents(
    deploy_target: Path,
    deployed_agents: list[str]
) -> int:
    """Remove agents managed by claude-mpm but no longer deployed.

    Args:
        deploy_target: Path to .claude/agents/ directory
        deployed_agents: List of agent filenames that should remain

    Returns:
        Number of agents removed
    """
```

### Integration

Called in `sync_remote_agents_on_startup()` after deployment:

```python
# After deployment completes
deployed_filenames = [
    f"{a}.md" for a in deployment_result.get("deployed", [])
] + [
    f"{a}.md" for a in deployment_result.get("updated", [])
] + [
    f"{a}.md" for a in deployment_result.get("skipped", [])
]

removed = _cleanup_orphaned_agents(deploy_target, deployed_filenames)
```

### Deployment Message

The deployment progress message includes cleanup results:

```
Complete: 3 deployed, 2 updated, 5 already present, 1 removed (10 configured from 45 in repo)
```

Or if no agents removed:

```
Complete: 3 deployed, 2 updated, 5 already present (10 configured from 45 in repo)
```

## Safety Considerations

1. **Never removes files without frontmatter** - could be user-created
2. **Only removes if frontmatter confirms claude-mpm ownership**
3. **Logs each removal** for debugging and audit trail
4. **Skips hidden files** (starting with `.`)
5. **Handles YAML parsing errors gracefully** - preserves file if parsing fails
6. **Non-blocking** - errors don't prevent startup

## Testing

Comprehensive test suite in `tests/test_orphaned_agent_cleanup.py`:

- Removes orphaned claude-mpm agents
- Preserves user agents without frontmatter
- Preserves user agents with custom frontmatter
- Handles multiple ownership marker combinations
- Skips hidden files
- Handles invalid YAML gracefully
- Works with empty directories
- Works with nonexistent directories

Run tests:

```bash
python -m pytest tests/test_orphaned_agent_cleanup.py -v
```

## Example Scenarios

### Scenario 1: Agent Removed from Configuration

**Before:**
```
.claude/agents/
├── python-engineer.md  (configured, deployed)
├── typescript-engineer.md  (configured, deployed)
└── old-agent.md  (NOT configured, orphaned)
```

**After cleanup:**
```
.claude/agents/
├── python-engineer.md  (configured, deployed)
└── typescript-engineer.md  (configured, deployed)
# old-agent.md removed (orphaned)
```

### Scenario 2: User Agent Preserved

**Before:**
```
.claude/agents/
├── python-engineer.md  (claude-mpm managed)
└── my-custom-agent.md  (user-created, no ownership markers)
```

**After cleanup:**
```
.claude/agents/
├── python-engineer.md  (configured, deployed)
└── my-custom-agent.md  (preserved - user agent)
```

### Scenario 3: Mixed Ownership Markers

**Before:**
```
.claude/agents/
├── agent-with-author.md  (author: Claude MPM Team)
├── agent-with-source.md  (source: remote)
├── agent-with-id.md  (agent_id: test-agent)
└── user-agent.md  (no markers)
```

**Configuration:** Only `user-agent` configured

**After cleanup:**
```
.claude/agents/
└── user-agent.md  (preserved)
# All claude-mpm agents removed (orphaned)
```

## Logging

Cleanup events are logged at appropriate levels:

- **INFO**: Each agent removed (for audit trail)
- **DEBUG**: YAML parsing errors or file access issues
- **WARNING**: (none - failures are silent to avoid blocking startup)

Example log output:

```
INFO: Removed orphaned agent: old-agent.md
DEBUG: Could not check agent hidden-file.md: YAML parsing error
```

## Performance

- **Fast**: Only scans `.md` files in `.claude/agents/`
- **Efficient**: Uses set lookups for O(1) membership checks
- **Non-blocking**: Runs as part of startup sync, doesn't delay CLI
- **Minimal I/O**: Only reads frontmatter (first few lines) of each file

## Future Enhancements

Potential improvements:

1. **Dry-run mode**: Show what would be removed without removing
2. **Backup before removal**: Move to `.claude/agents/.orphaned/`
3. **Confirmation prompt**: Ask user before removing (optional)
4. **Batch reporting**: Summary of all removals in single message
5. **Selective cleanup**: Only clean specific agents or patterns

## Related Documentation

- [Agent Deployment](./agent-deployment.md)
- [Agent Configuration](../configuration/agents.md)
- [Startup Sync](./startup-sync.md)

## Changelog

### v5.4.7 (2025-01-XX)

- Initial implementation of orphaned agent cleanup
- Added comprehensive test suite
- Integrated into startup sync workflow
- Added deployment message updates
