# Update Checking System

The claude-mpm update checking system automatically notifies users of new versions and provides an easy upgrade path. It also verifies Claude Code compatibility.

## Features

### 1. Automatic Update Detection
- Checks PyPI for Python packages (pip/pipx installations)
- Checks npm registry for npm installations
- Runs in background thread (non-blocking)
- Caches results to avoid excessive API calls (24-hour default)
- Graceful failure handling (never blocks startup)

### 2. Claude Code Compatibility Checking
- Detects installed Claude Code version via `claude --version`
- Compares against minimum required version (1.0.92)
- Recommends optimal version (2.0.30+)
- Provides actionable error messages for missing/outdated installations

### 3. Smart Notifications
- Clean, formatted update messages with release notes links
- Displays upgrade command for user's installation method
- Non-interactive by default (doesn't interrupt workflow)
- Optional interactive prompts for manual upgrades

## Configuration

Update checking behavior is controlled via `~/.claude-mpm/configuration.yaml`:

```yaml
updates:
  # Enable/disable automatic update checks
  check_enabled: true

  # Check frequency: "always", "daily", "weekly", or "never"
  check_frequency: "daily"

  # Check Claude Code version compatibility
  check_claude_code: true

  # Automatically upgrade without prompting (use with caution)
  auto_upgrade: false

  # Cache TTL in seconds (default: 24 hours)
  cache_ttl: 86400
```

### Frequency Options

- **always**: Check on every startup (uses cache to avoid excessive API calls)
- **daily**: Check once per day (default)
- **weekly**: Check once per week
- **never**: Disable update checking completely

### Environment Variables

Update checking respects the following environment variables:

```bash
# Disable all update checking
export CLAUDE_MPM_SKIP_UPDATE_CHECK=1

# Set custom cache TTL (in seconds)
export CLAUDE_MPM_UPDATE_CACHE_TTL=3600
```

## Installation Method Detection

The system automatically detects how claude-mpm was installed:

- **pipx**: Recommends `pipx upgrade claude-mpm`
- **pip**: Recommends `pip install --upgrade claude-mpm`
- **npm**: Recommends `npm update -g claude-mpm`
- **editable**: Recommends `git pull && pip install -e .` (skips auto-checks)

## Example Output

### Update Available
```
ℹ️  Update available: v4.21.2 → v4.21.3
   Run: pipx upgrade claude-mpm
   Release notes: https://github.com/bobmatnyc/claude-mpm/releases/tag/v4.21.3
```

### Claude Code Not Installed
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

### Interactive Upgrade Prompt
```
======================================================================
📢 Update Available for claude-mpm
======================================================================
   Current: v4.21.2
   Latest:  v4.21.3
   Method:  pipx

   Upgrade: pipx upgrade claude-mpm
   Release: https://github.com/bobmatnyc/claude-mpm/releases/tag/v4.21.3
======================================================================

Would you like to upgrade now? [y/N]:
```

## Manual Update Checking

You can manually check for updates using the upgrade service:

```python
from claude_mpm.services.self_upgrade_service import SelfUpgradeService
import asyncio

async def check_updates():
    service = SelfUpgradeService()

    # Check for claude-mpm updates
    update_info = await service.check_for_update()
    if update_info and update_info['update_available']:
        print(f"Update available: {update_info['latest']}")

    # Check Claude Code compatibility
    claude_compat = service.check_claude_code_compatibility()
    print(f"Claude Code: {claude_compat['message']}")

asyncio.run(check_updates())
```

## CLI Commands

### Check for Updates
```bash
# Check and display available updates (planned)
claude-mpm upgrade --check

# Perform upgrade with confirmation
claude-mpm upgrade

# Auto-upgrade without confirmation (use with caution)
claude-mpm upgrade --yes
```

### Disable Update Checking
```bash
# Temporarily disable for single command
CLAUDE_MPM_SKIP_UPDATE_CHECK=1 claude-mpm run

# Disable permanently via configuration
claude-mpm configure
# Then set: updates.check_enabled = false
```

## Architecture

### Components

1. **SelfUpgradeService** (`services/self_upgrade_service.py`)
   - Main upgrade service with version checking
   - Installation method detection
   - Claude Code compatibility checking
   - Upgrade execution and process restart

2. **PackageVersionChecker** (`services/mcp_gateway/utils/package_version_checker.py`)
   - PyPI API client with caching
   - Timeout handling and error recovery
   - Cache management (~/.cache/claude-mpm/version-checks/)

3. **Startup Integration** (`cli/startup.py`)
   - Background thread execution
   - Configuration loading and validation
   - Non-blocking async checks

### Cache Location

Update check results are cached in:
```
~/.cache/claude-mpm/version-checks/
├── claude-mpm.json
└── kuzu-memory.json
```

Cache files contain:
```json
{
  "current": "4.21.2",
  "latest": "4.21.3",
  "update_available": true,
  "checked_at": "2025-01-29T12:00:00+00:00"
}
```

## Error Handling

The update checking system follows these principles:

1. **Never Block Startup**: All checks run in background threads
2. **Graceful Degradation**: Network failures don't prevent normal operation
3. **Timeout Protection**: PyPI/npm requests timeout after 5 seconds
4. **Silent Failures**: Errors logged to debug level, not shown to users
5. **Cache Fallback**: Uses cached data if network unavailable

## Testing

### Unit Tests
```bash
# Test version detection
pytest tests/unit/test_version_checker.py

# Test installation method detection
pytest tests/unit/test_upgrade_service.py

# Test Claude Code compatibility checking
pytest tests/unit/test_claude_code_version.py
```

### Integration Tests
```bash
# Test full upgrade flow
pytest tests/integration/test_upgrade_flow.py

# Test with different installation methods
pytest tests/integration/test_install_methods.py
```

### Manual Testing
```bash
# Test update notification
# (Temporarily modify current version to trigger notification)
claude-mpm --version

# Test Claude Code detection
claude --version

# Test with disabled checks
CLAUDE_MPM_SKIP_UPDATE_CHECK=1 claude-mpm run
```

## Troubleshooting

### Update Check Not Running
1. Check configuration: `cat ~/.claude-mpm/configuration.yaml | grep -A 5 updates`
2. Verify not disabled: `echo $CLAUDE_MPM_SKIP_UPDATE_CHECK`
3. Check logs: `claude-mpm --debug run` (look for "upgrade_check" messages)

### Claude Code Not Detected
1. Verify installation: `which claude`
2. Check version output: `claude --version`
3. Ensure Claude Code is in PATH: `echo $PATH | grep claude`

### Cache Issues
1. Clear cache: `rm -rf ~/.cache/claude-mpm/version-checks/`
2. Force fresh check: delete cache files manually
3. Check cache permissions: `ls -la ~/.cache/claude-mpm/`

### Network Timeouts
1. Check internet connectivity
2. Verify PyPI access: `curl -I https://pypi.org/pypi/claude-mpm/json`
3. Increase timeout in code if needed (default: 5 seconds)

## Security Considerations

1. **No Automatic Installation**: Updates are never installed without user consent (unless `auto_upgrade: true`)
2. **HTTPS Only**: All API calls use HTTPS
3. **Signature Verification**: Relies on package manager's built-in verification (pip/pipx/npm)
4. **No Credential Storage**: No authentication required for update checks
5. **Cache Security**: Cache files stored in user-owned directory with standard permissions

## Future Enhancements

Planned improvements:

1. **Release Notes Display**: Show changelog in update notification
2. **Selective Updates**: Allow pinning to specific versions
3. **Update Channels**: Support beta/stable channels
4. **Notification Preferences**: Email/desktop notifications
5. **Automatic Dependency Updates**: Check for outdated dependencies
6. **Rollback Support**: Easy rollback to previous version
7. **Update Statistics**: Track update adoption rates

## Related Documentation

- [Configuration Guide](./configuration.md)
- [CLI Reference](./cli-reference.md)
- [Self-Hosting Guide](./self-hosting.md)
- [Development Setup](./development.md)
