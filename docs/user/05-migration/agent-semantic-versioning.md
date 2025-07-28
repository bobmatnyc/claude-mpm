# Agent Semantic Versioning Migration Guide

This guide explains the migration from serial versioning to semantic versioning for Claude MPM agents.

## Overview of Changes

Claude MPM has migrated from a serial versioning system (e.g., `0002-0005`) to semantic versioning (e.g., `2.1.0`) for agent templates. This change provides:

- **Clearer version progression**: Understanding major vs minor vs patch updates
- **Better compatibility tracking**: Knowing when breaking changes occur
- **Industry standard format**: Following widely adopted semantic versioning
- **Automatic migration**: System handles conversion automatically

## Version Format Changes

### Old Serial Format
```yaml
---
name: research_agent
version: "0002-0005"  # base-agent version
---
```

### New Semantic Format
```yaml
---
name: research_agent
version: "2.1.0"  # semantic version
metadata:
  base_version: "2.0.0"
  agent_version: "2.1.0"
---
```

## Understanding Semantic Versions

### Version Components
- **Major (2.x.x)**: Breaking changes to agent behavior or API
- **Minor (x.1.x)**: New capabilities, enhancements, backward compatible
- **Patch (x.x.0)**: Bug fixes, minor improvements, fully compatible

### Version Comparison
```
2.1.0 > 2.0.0  # Newer minor version
2.1.0 > 1.9.9  # Newer major version
2.1.1 > 2.1.0  # Newer patch version
```

## Automatic Migration

The agent deployment system automatically detects and migrates old version formats:

### Detection Triggers
1. **Serial format**: `XXXX-YYYY` pattern
2. **Missing version**: No version field in frontmatter
3. **Integer format**: Simple numbers like `5`
4. **Old metadata**: `agent_version: 5` in separate field

### Migration Process
1. System detects old format during deployment
2. Logs the detection: "Detected old serial version format: 0002-0005"
3. Converts to semantic version automatically
4. Updates the deployed agent file
5. Reports migration in deployment results

## How to Migrate

### Option 1: Automatic Migration (Recommended)

Simply deploy your agents normally - migration happens automatically:

```bash
# Deploy agents (includes automatic migration)
claude-mpm agents deploy

# Check migration results
claude-mpm agents verify
```

### Option 2: Force Migration

To force migration of all agents:

```bash
# Force rebuild all agents
claude-mpm agents deploy --force-rebuild
```

### Option 3: Manual Migration

If you need to manually update agent templates:

1. **Update template JSON files**:
   ```json
   {
     "agent_version": "2.1.0",  // Change from integer to semantic
     "metadata": {
       "updated_at": "2025-07-27T12:00:00.000000Z"
     }
   }
   ```

2. **Deploy the updated agents**:
   ```bash
   claude-mpm agents deploy
   ```

## Verification

### Check Current Versions

```bash
# List all agents with versions
claude-mpm agents list

# Verify deployment status
claude-mpm agents verify
```

### Sample Output
```
Agents needing migration:
- research_agent (version: 0002-0005)
- engineer_agent (version: missing)

Deployed agents:
- qa_agent (version: 2.1.0) ✓
- security_agent (version: 2.0.1) ✓
```

## Migration Results

After migration, the deployment command reports:

```json
{
  "deployed": [...],
  "updated": [...],
  "migrated": [
    {
      "name": "research_agent",
      "reason": "migration needed: old format 0002-0005 -> 2.1.0"
    }
  ]
}
```

## Version Update Workflow

### For Agent Developers

1. **Update agent template**:
   ```json
   {
     "agent_version": "2.2.0",  // Increment version
     "metadata": {
       "updated_at": "2025-07-27T14:00:00.000000Z"
     }
   }
   ```

2. **Test locally**:
   ```bash
   claude-mpm agents deploy --force-rebuild
   claude-mpm agents verify
   ```

3. **Commit changes**:
   ```bash
   git add src/claude_mpm/agents/templates/
   git commit -m "feat(agents): enhance research agent capabilities"
   ```

### For Users

Agents update automatically when:
- Running `claude-mpm agents deploy`
- Template version increases
- Old format needs migration

## Troubleshooting

### Issue: Agents Not Migrating

**Symptom**: Old version format persists after deployment

**Solution**:
```bash
# Force rebuild
claude-mpm agents deploy --force-rebuild

# Check logs for errors
claude-mpm agents deploy --debug
```

### Issue: Version Comparison Issues

**Symptom**: Newer agents not deploying over older ones

**Check**:
1. Verify template version is higher
2. Check for syntax errors in version string
3. Use force rebuild if needed

### Issue: Custom Agents

**For custom agents not managed by claude-mpm**:
- Manual migration may be needed
- Update version field to semantic format
- Ensure YAML frontmatter is valid

## Best Practices

1. **Use semantic versioning** for all new agents
2. **Increment versions** when making changes:
   - Major: Breaking changes
   - Minor: New features
   - Patch: Bug fixes
3. **Document changes** in commit messages
4. **Test deployment** before committing
5. **Monitor migration logs** for issues

## Developer Reference

### Version Parsing Logic

The system handles various formats:
```python
# Integer -> Semantic
5 -> (0, 5, 0) -> "2.1.0"

# String integer -> Semantic  
"5" -> (0, 5, 0) -> "2.1.0"

# Serial format -> Semantic
"0002-0005" -> (0, 5, 0) -> "2.1.0"

# Already semantic -> No change
"2.1.0" -> (2, 1, 0) -> "2.1.0"
```

### File Locations

- **Templates**: `src/claude_mpm/agents/templates/*.json`
- **Deployed agents**: `~/.claude/agents/*.md`
- **Deployment service**: `src/claude_mpm/services/agent_deployment.py`

## Summary

The migration to semantic versioning:
- Happens automatically during deployment
- Provides clearer version tracking
- Follows industry standards
- Maintains backward compatibility
- Improves update detection

No manual intervention is required for most users - the system handles migration transparently during normal operations.