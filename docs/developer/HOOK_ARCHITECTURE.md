# Hook Architecture (Deployment-Root)

## Overview

As of v4.1.8+, Claude MPM uses a **deployment-root hook architecture** where Claude Code hooks directly call a script within the claude-mpm installation, eliminating the need to deploy scripts to `~/.claude/hooks/`.

## Architecture Benefits

### Previous Architecture (Deprecated)
- Deployed `claude-mpm-hook.sh` to `~/.claude/hooks/`
- Script had to dynamically find claude-mpm installation
- Complex logic to handle different installation methods
- Fragile and could break if installation changed
- Required file deployment and management

### New Architecture (Deployment-Root)
- Claude hooks directly call `<installation>/src/claude_mpm/scripts/claude-hook-handler.sh`
- Script is part of the package - no deployment needed
- Environment setup is centralized and reliable
- Updates are immediate (no redeployment)
- Works consistently across all installation methods

## Implementation Details

### Hook Script Location

The hook handler script is located at:
- **Development**: `{project_root}/src/claude_mpm/scripts/claude-hook-handler.sh`
- **Pip Install**: `{site-packages}/claude_mpm/scripts/claude-hook-handler.sh`

### Script Responsibilities

The `claude-hook-handler.sh` script handles:
1. Python environment detection (venv, .venv, system)
2. PYTHONPATH configuration for development installs
3. Socket.IO port configuration
4. Error handling to prevent blocking Claude Code
5. Debug logging (when `CLAUDE_MPM_HOOK_DEBUG=true`)

### Installation Process

When hooks are installed via `claude-mpm configure hooks install`:

1. **Locate Script**: The installer finds the hook script based on the installation method
2. **Make Executable**: Ensures the script has execute permissions
3. **Update Settings**: Updates `~/.claude/settings.json` to point directly to the script
4. **Clean Up**: Removes any old deployed scripts from `~/.claude/hooks/`

### Settings Configuration

The `~/.claude/settings.json` is configured with absolute paths to the deployment-root script:

```json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "/path/to/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh"
      }]
    }],
    // ... other event types
  }
}
```

## Development Guidelines

### Testing Hooks

```bash
# Test hook script detection
python -c "from claude_mpm.hooks.claude_hooks.installer import HookInstaller; \
          installer = HookInstaller(); \
          path = installer.get_hook_script_path(); \
          print(f'Script: {path}'); \
          print(f'Exists: {path.exists()}')"

# Test with sample event
echo '{"type": "Stop", "timestamp": "2025-01-26T10:00:00Z"}' | \
  /path/to/src/claude_mpm/scripts/claude-hook-handler.sh

# Enable debug logging
export CLAUDE_MPM_HOOK_DEBUG=true
tail -f /tmp/claude-mpm-hook.log
```

### Modifying the Hook Handler

If you need to modify the hook handler:

1. Edit `/src/claude_mpm/scripts/claude-hook-handler.sh`
2. Changes take effect immediately (no reinstallation needed)
3. Test with sample events before using with Claude Code

### Package Distribution

The script is included in the package via `pyproject.toml`:

```toml
[tool.setuptools.package-data]
claude_mpm = [
    "scripts/*",  # Includes all scripts in the package
    # ... other package data
]
```

## Migration from Old Architecture

Users upgrading from older versions will automatically migrate to the deployment-root architecture when they run:

```bash
claude-mpm configure hooks install --force
```

This will:
1. Update settings to use deployment-root script
2. Remove old deployed scripts from `~/.claude/hooks/`
3. Preserve any custom hook configurations

## Troubleshooting

### Script Not Found

If the hook script cannot be found:

1. Verify claude-mpm is properly installed
2. Check the script exists: `ls -la $(python -c "import claude_mpm; print(claude_mpm.__file__.replace('__init__.py', 'scripts/'))")`
3. Reinstall claude-mpm if necessary: `pip install -e .` (for development)

### Permission Denied

If you get permission errors:

1. Ensure the script is executable: `chmod +x /path/to/scripts/claude-hook-handler.sh`
2. Check file ownership and permissions
3. Run hook installation with proper permissions

### Hook Not Triggering

If hooks don't trigger in Claude Code:

1. Verify Claude Code version: `claude --version` (requires 1.0.92+)
2. Check settings: `cat ~/.claude/settings.json | jq .hooks`
3. Enable debug logging: `export CLAUDE_MPM_HOOK_DEBUG=true`
4. Check logs: `tail -f /tmp/claude-mpm-hook.log`

## Version Compatibility

- **Claude Code**: Requires version 1.0.92 or higher for matcher-based hooks
- **Claude MPM**: Deployment-root architecture available in v4.1.8+
- **Python**: Compatible with Python 3.9+