# Base Agent Loading Priority System

## Issue Fixed

The base agent (`base_agent.json`) was being loaded from the pipx installation directory instead of the local development build when running in development mode. This prevented developers from testing changes to the base agent without reinstalling the package.

## Solution Implemented

Implemented a priority-based search system for locating `base_agent.json` that checks multiple locations in order of preference.

## Priority Order

The system now searches for `base_agent.json` in the following order:

1. **Environment Variable Override** (`CLAUDE_MPM_BASE_AGENT_PATH`)
   - Allows explicit override for testing specific base agent files
   - Useful for CI/CD and testing scenarios

2. **Current Working Directory** (for local development)
   - Checks `{cwd}/src/claude_mpm/agents/base_agent.json`
   - Enables testing local changes without reinstalling

3. **Known Development Locations**
   - `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json`
   - `~/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json`
   - Common development directory locations

4. **User Override Location**
   - `~/.claude/agents/base_agent.json`
   - Allows user-specific customizations

5. **Package Installation Location** (fallback)
   - The installed package's agents directory
   - Used when running from pip/pipx installations outside development

## Files Modified

### Core Module
- `src/claude_mpm/agents/base_agent_loader.py`
  - Updated `_get_base_agent_file()` function with priority-based search
  - Added environment variable support
  - Improved logging to show which path is being used

### Deployment Services
- `src/claude_mpm/services/agents/deployment/agent_deployment.py`
  - Added `_find_base_agent_file()` method with same priority logic
  - Updated initialization to use priority-based search

- `src/claude_mpm/services/agents/deployment/async_agent_deployment.py`
  - Added `_find_base_agent_file()` method with same priority logic
  - Updated initialization to use priority-based search

### Test Utilities
- `scripts/test_base_agent_loading.py` (new)
  - Comprehensive test script to verify base agent loading
  - Tests all three main components that load base agents
  - Shows clear output indicating which version is being used

## Usage

### For Development

When working in the claude-mpm development directory:
```bash
# Running from development directory automatically uses local base_agent.json
cd /Users/masa/Projects/claude-mpm
python -m claude_mpm.cli agents deploy
```

### With Environment Variable

Force a specific base agent file:
```bash
export CLAUDE_MPM_BASE_AGENT_PATH=/path/to/custom/base_agent.json
claude-mpm agents deploy
```

### Testing the Fix

Run the test script to verify proper loading:
```bash
python scripts/test_base_agent_loading.py
```

Expected output should show:
- ✓ Using LOCAL DEVELOPMENT version (correct!)
- All tests passing

## Benefits

1. **Development Efficiency**: Developers can test base agent changes immediately without reinstalling
2. **Flexibility**: Environment variable allows testing different base agent configurations
3. **Backward Compatibility**: Falls back to installed version when not in development
4. **Clear Debugging**: Logs clearly show which base agent path is being used
5. **Consistent Behavior**: All components use the same priority logic

## Future Improvements

Consider adding:
- Configuration file option for base agent path
- Command-line flag to override base agent location
- Caching mechanism that respects development mode
- Automatic detection of editable pip installs