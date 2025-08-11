# Registry Deployment Root Fix

## Overview
Fixed the ProjectRegistry service and related components to use the deployment root's registry instead of the user's home directory. This ensures all claude-mpm data is centralized with the installation rather than scattered across user directories.

## Problem
The current implementation incorrectly used `~/.claude-mpm/registry/` when it should use `[deployment-root]/.claude-mpm/registry/` where deployment-root is the root directory of the claude-mpm installation.

## Solution
Updated all relevant services to use `get_project_root()` from `deployment_paths.py` to determine the correct deployment root, then use that for all claude-mpm data storage.

## Files Modified

### Core Registry Services
1. **src/claude_mpm/services/project_registry.py**
   - Changed `Path.home() / ".claude-mpm" / "registry"` to `get_project_root() / ".claude-mpm" / "registry"`
   - Updated docstrings to reflect the new location

2. **src/claude_mpm/manager/discovery.py**
   - InstallationDiscovery now uses deployment root for manager config
   - Changed config path from `Path.home() / ".claude-mpm" / "manager" / "config.yaml"` to deployment root

3. **src/claude_mpm/manager/config/manager_config.py**
   - ManagerConfig.load() and save() now use deployment root
   - Configuration stored at `[deployment-root]/.claude-mpm/manager/config.yaml`

4. **src/claude_mpm/manager_textual/config/manager_config.py**
   - Updated get_config_path() to use deployment root

5. **src/claude_mpm/manager_textual/discovery.py**
   - Updated to use deployment root for manager config

### Additional Services Updated
1. **src/claude_mpm/scripts/socketio_daemon.py**
   - PID and log files now stored in deployment root
   - `[deployment-root]/.claude-mpm/socketio-server.pid`
   - `[deployment-root]/.claude-mpm/socketio-server.log`

2. **src/claude_mpm/core/logger.py**
   - Default log directory now uses deployment root
   - Logs stored at `[deployment-root]/.claude-mpm/logs/`

3. **src/claude_mpm/services/simple_instructions_synthesizer.py**
   - Now checks deployment root first for custom INSTRUCTIONS.md
   - Falls back to user home for backward compatibility
   - Priority: `[deployment-root]/.claude-mpm/INSTRUCTIONS.md` then `~/.claude-mpm/INSTRUCTIONS.md`

## Benefits
1. **Centralized Data**: All claude-mpm data (registry, configs, logs, etc.) is now stored with the installation
2. **Better Organization**: Easier to manage and backup claude-mpm data
3. **Consistency**: All services use the same deployment root pattern
4. **Backward Compatibility**: Some services (like instructions synthesizer) still check user home as fallback

## Testing
Created test file `tests/test_registry_deployment_root.py` that verifies:
- ProjectRegistry uses deployment root
- InstallationDiscovery uses deployment root for config
- ManagerConfig uses deployment root
- Registry is not using the hardcoded home directory path

## Migration Notes
For existing installations:
1. Any existing registry data in `~/.claude-mpm/registry/` will need to be manually migrated to `[deployment-root]/.claude-mpm/registry/`
2. Manager configurations in `~/.claude-mpm/manager/config.yaml` should be moved to the deployment root
3. Custom INSTRUCTIONS.md files can remain in user home (backward compatible) or be moved to deployment root for consistency

## Future Considerations
1. Consider adding automatic migration of existing data from user home to deployment root
2. May want to add configuration option to allow users to specify custom data directory
3. Could add environment variable support (e.g., `CLAUDE_MPM_DATA_DIR`) for custom locations