# Quick Reference: Update Checking

## Overview
Automatic update checking with Claude Code compatibility verification.

## Configuration

Edit `~/.claude-mpm/configuration.yaml`:

```yaml
updates:
  check_enabled: true          # Enable/disable checks
  check_frequency: "daily"     # always|daily|weekly|never
  check_claude_code: true      # Check Claude Code compatibility
  auto_upgrade: false          # Auto-upgrade (use with caution)
  cache_ttl: 86400            # Cache time-to-live (seconds)
```

## Quick Disable

```bash
# Temporarily disable
export CLAUDE_MPM_SKIP_UPDATE_CHECK=1

# Or in configuration
updates:
  check_enabled: false
```

## Example Outputs

### Update Available
```
ℹ️  Update available: v4.21.2 → v4.21.3
   Run: pipx upgrade claude-mpm
   Release notes: https://github.com/bobmatnyc/claude-mpm/releases/tag/v4.21.3
```

### Claude Code Missing
```
⚠️  Claude Code Not Detected
   Claude Code is not installed or not in PATH.
   Install from: https://docs.anthropic.com/en/docs/claude-code
```

### Claude Code Outdated
```
⚠️  Claude Code Outdated
   Claude Code v1.0.50 is outdated
   Minimum required: v1.0.92
   Recommended: v2.0.30+
```

## Troubleshooting

### Clear Cache
```bash
rm -rf ~/.cache/claude-mpm/version-checks/
```

### Check Current Versions
```bash
claude-mpm --version
claude --version
```

### Debug Mode
```bash
claude-mpm --debug run
```

## Version Requirements

- **claude-mpm**: Latest from PyPI
- **Claude Code**:
  - Minimum: v1.0.92
  - Recommended: v2.0.30+

## Related Files

- Configuration: `~/.claude-mpm/configuration.yaml`
- Cache: `~/.cache/claude-mpm/version-checks/`
- Documentation: `docs/update-checking.md`

## Key Features

✅ Non-blocking background checks
✅ Respects user configuration
✅ Caches results (24 hours default)
✅ Claude Code compatibility checking
✅ Installation method detection (pip/pipx/npm)
✅ Graceful error handling

## Support

- Full docs: `docs/update-checking.md`
- Issues: https://github.com/bobmatnyc/claude-mpm/issues
