# Agent Semantic Versioning - Summary

## Overview

Claude MPM has migrated from serial versioning (e.g., `0002-0005`) to semantic versioning (e.g., `2.1.0`) for agent templates. This change provides clearer version tracking and follows industry standards.

## Key Changes

### Version Format
- **Old**: `0002-0005` (serial format)
- **New**: `2.1.0` (semantic format: major.minor.patch)

### Auto-Migration
The system automatically detects and migrates old formats during deployment:
- Serial format → Semantic version
- Integer versions → Semantic version
- Missing versions → Default semantic version

### Version Comparison
```
2.1.0 > 2.0.0  # Newer minor version
2.1.0 > 1.9.9  # Newer major version
2.1.1 > 2.1.0  # Newer patch version
```

## Usage

### Deploy Agents (with auto-migration)
```bash
claude-mpm agents deploy
```

### Force Migration
```bash
claude-mpm agents deploy --force-rebuild
```

### Verify Versions
```bash
claude-mpm agents verify
claude-mpm agents list
```

## Developer Guide

### Update Agent Version
Edit template JSON file:
```json
{
  "agent_version": "2.2.0",  // Increment version
  "metadata": {
    "updated_at": "2025-07-27T12:00:00.000000Z"
  }
}
```

### Version Guidelines
- **Major (X.0.0)**: Breaking changes
- **Minor (x.X.0)**: New features, backward compatible
- **Patch (x.x.X)**: Bug fixes, minor improvements

## Documentation

- **User Guide**: [docs/user/05-migration/agent-semantic-versioning.md](docs/user/05-migration/agent-semantic-versioning.md)
- **Developer Guide**: [docs/developer/02-core-components/agent-versioning.md](docs/developer/02-core-components/agent-versioning.md)
- **Version Management**: [docs/VERSIONING.md](docs/VERSIONING.md) (includes agent versioning section)
- **Deployment**: [docs/DEPLOY.md](docs/DEPLOY.md) (includes agent deployment section)

## Benefits

1. **Standardized**: Follows semantic versioning standard
2. **Automatic**: Migration happens transparently during deployment
3. **Clear**: Easy to understand version progression
4. **Compatible**: Maintains backward compatibility with old formats

## Technical Implementation

- **Service**: `src/claude_mpm/services/agent_deployment.py`
- **Version Parser**: `_parse_version()` method
- **Format Detector**: `_is_old_version_format()` method
- **Version Display**: `_format_version_display()` method

## Troubleshooting

If agents aren't migrating:
1. Run `claude-mpm agents deploy --force-rebuild`
2. Check logs: `claude-mpm agents deploy --debug`
3. Verify template JSON has valid `agent_version` field

## Summary

The migration to semantic versioning is automatic and requires no manual intervention for most users. The system handles all format conversions transparently during normal agent deployment operations.