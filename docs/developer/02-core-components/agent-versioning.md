# Agent Versioning System

Technical documentation for the agent semantic versioning system in Claude MPM.

## Overview

The agent versioning system provides semantic version management for agent templates, automatic migration from legacy formats, and intelligent update detection.

## Architecture

### Key Components

1. **AgentDeploymentService** (`src/claude_mpm/services/agent_deployment.py`)
   - Handles agent deployment and version management
   - Detects and migrates old version formats
   - Compares versions for update decisions

2. **Version Storage**
   - Template JSON files: `agent_version` field
   - Deployed agent files: YAML frontmatter `version` field
   - Metadata tracking: `base_version` and `agent_version`

## Version Format

### Semantic Version Structure
```python
# Tuple representation: (major, minor, patch)
(2, 1, 0)  # Version 2.1.0
```

### JSON Template Format
```json
{
  "schema_version": "1.0.0",
  "agent_id": "research_agent",
  "agent_version": "2.1.0",  // Semantic version
  "metadata": {
    "name": "Research Agent",
    "updated_at": "2025-07-27T10:30:00.000000Z"
  }
}
```

### Deployed Agent Format
```yaml
---
name: research_agent
version: "2.1.0"
metadata:
  base_version: "2.0.0"
  agent_version: "2.1.0"
---
```

## Version Parsing

### `_parse_version()` Method

Handles multiple input formats:

```python
def _parse_version(self, version_value: Any) -> tuple:
    """
    Parse version from various formats to semantic version tuple.
    
    Examples:
    - Integer: 5 -> (0, 5, 0)
    - String integer: "5" -> (0, 5, 0)
    - Semantic: "2.1.0" -> (2, 1, 0)
    - Invalid: returns (0, 0, 0)
    """
```

### Supported Input Formats

1. **Integer values**: `5` → `(0, 5, 0)`
2. **String integers**: `"5"` → `(0, 5, 0)`
3. **Semantic versions**: `"2.1.0"` or `"v2.1.0"` → `(2, 1, 0)`
4. **Invalid formats**: Default to `(0, 0, 0)`

## Version Comparison

### Tuple-Based Comparison

Version tuples are compared lexicographically:

```python
# Examples
(2, 1, 0) > (2, 0, 0)  # True - newer minor
(2, 1, 0) > (1, 9, 9)  # True - newer major
(2, 1, 1) > (2, 1, 0)  # True - newer patch
```

### Update Detection Logic

```python
def _check_agent_needs_update(self, deployed_file, template_file, base_version):
    # 1. Extract deployed version
    # 2. Check for old format (triggers migration)
    # 3. Compare with template version
    # 4. Return (needs_update, reason)
```

## Migration System

### Old Format Detection

The `_is_old_version_format()` method detects:

1. **Serial format**: `^\d+-\d+$` (e.g., "0002-0005")
2. **Missing version**: No version field
3. **Non-semantic**: Any format not matching `^v?\d+\.\d+\.\d+$`

### Migration Process

1. **Detection Phase**
   ```python
   if self._is_old_version_format(version_str):
       is_old_format = True
       # Log detection
       self.logger.info(f"Detected old format: {version_str}")
   ```

2. **Conversion Phase**
   - Serial `"0002-0005"` → Extract agent part → `(0, 5, 0)`
   - Integer `5` → `(0, 5, 0)`
   - Missing → `(0, 0, 0)`

3. **Display Phase**
   ```python
   def _format_version_display(self, version_tuple):
       # (0, 5, 0) -> "2.1.0"
       # Standardizes display format
   ```

## Deployment Behavior

### Update Triggers

Agents are redeployed when:

```python
# Version increase
template_version > deployed_version

# Format migration needed
is_old_format == True

# Force rebuild
force_rebuild == True

# Base version update
new_base_version > deployed_base_version
```

### Deployment Results

```python
results = {
    "deployed": [],      # New agents
    "updated": [],       # Version updates
    "migrated": [],      # Format migrations
    "skipped": [],       # Up-to-date agents
    "errors": []         # Failed deployments
}
```

## Implementation Details

### Key Methods

1. **`deploy_agents()`**
   - Main deployment orchestrator
   - Handles migration and updates
   - Returns detailed results

2. **`_build_agent_markdown()`**
   - Constructs agent file with version metadata
   - Combines base and agent templates
   - Formats YAML frontmatter

3. **`_check_agent_needs_update()`**
   - Compares deployed vs template versions
   - Detects old formats
   - Returns update decision and reason

4. **`verify_deployment()`**
   - Lists deployed agents
   - Identifies agents needing migration
   - Provides deployment status

## Version Update Workflow

### For Developers

1. **Update template version**:
   ```json
   {
     "agent_version": "2.2.0"  // Increment
   }
   ```

2. **Deploy locally**:
   ```bash
   claude-mpm agents deploy --force-rebuild
   ```

3. **Verify deployment**:
   ```bash
   claude-mpm agents verify
   ```

### Version Increment Guidelines

- **Major (X.0.0)**: Breaking changes
  - Changed agent API
  - Removed capabilities
  - Incompatible behavior changes

- **Minor (x.X.0)**: New features
  - Added capabilities
  - Enhanced functionality
  - Backward compatible changes

- **Patch (x.x.X)**: Bug fixes
  - Fixed errors
  - Performance improvements
  - Documentation updates

## Error Handling

### Common Scenarios

1. **Invalid version format**:
   - Defaults to (0, 0, 0)
   - Logs warning
   - Continues deployment

2. **Missing template**:
   - Logs error
   - Adds to errors array
   - Continues with other agents

3. **Write failures**:
   - Logs specific error
   - Reports in results
   - Does not affect other agents

## Testing

### Unit Test Coverage

```python
# Test version parsing
assert _parse_version("2.1.0") == (2, 1, 0)
assert _parse_version(5) == (0, 5, 0)
assert _parse_version("invalid") == (0, 0, 0)

# Test format detection
assert _is_old_version_format("0002-0005") == True
assert _is_old_version_format("2.1.0") == False

# Test version comparison
assert (2, 1, 0) > (2, 0, 0)
```

### Integration Testing

1. Deploy agents with old formats
2. Verify automatic migration
3. Check version display
4. Confirm update behavior

## Future Enhancements

### Planned Features

1. **Version history tracking**
   - Store version upgrade history
   - Track migration timestamps
   - Provide rollback capability

2. **Version constraints**
   - Minimum version requirements
   - Compatibility matrices
   - Dependency management

3. **Automated version bumping**
   - Analyze changes to suggest version
   - Integrate with CI/CD
   - Auto-increment on merge

## Best Practices

1. **Always use semantic versioning** for new agents
2. **Document version changes** in commit messages
3. **Test migrations** before deployment
4. **Monitor deployment logs** for issues
5. **Keep versions synchronized** across environments

## Troubleshooting

### Debug Commands

```bash
# Enable debug logging
claude-mpm agents deploy --debug

# Check specific agent
claude-mpm agents verify | grep agent_name

# Force specific agent rebuild
rm ~/.claude/agents/agent_name.md
claude-mpm agents deploy
```

### Common Issues

1. **Version not updating**
   - Check template version is higher
   - Verify file permissions
   - Use force rebuild flag

2. **Migration failing**
   - Check agent file format
   - Look for syntax errors
   - Review deployment logs

3. **Comparison issues**
   - Verify version string format
   - Check for special characters
   - Ensure proper quotes in YAML