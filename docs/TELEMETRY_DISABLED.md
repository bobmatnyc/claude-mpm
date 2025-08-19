# Telemetry Disabled for Claude Code

## Overview

As of this update, claude-mpm automatically sets the `DISABLE_TELEMETRY=1` environment variable when launching Claude Code. This ensures that Claude Code does not collect or send telemetry data during runtime.

## Implementation Details

The `DISABLE_TELEMETRY=1` environment variable is set in the following locations:

1. **Interactive Sessions** (`src/claude_mpm/core/interactive_session.py`)
   - Set in `_prepare_environment()` method
   - Applied when running `claude-mpm run` in interactive mode

2. **Oneshot Sessions** (`src/claude_mpm/core/oneshot_session.py`)
   - Set in `_prepare_environment()` method
   - Applied when running `claude-mpm run` with non-interactive commands

3. **Subprocess Launcher** (`src/claude_mpm/services/subprocess_launcher_service.py`)
   - Set in `prepare_subprocess_environment()` method
   - Applied when using `--launch-method subprocess`

## Why This Matters

- **Privacy**: Prevents Claude Code from sending usage data or telemetry
- **Security**: Reduces potential data leakage in sensitive environments
- **Performance**: Eliminates network overhead from telemetry reporting
- **Compliance**: Helps meet data privacy requirements in regulated environments

## Technical Implementation

The environment variable is set just before Claude Code is launched:

```python
def _prepare_environment(self) -> dict:
    """Prepare clean environment variables for Claude."""
    clean_env = os.environ.copy()
    
    # ... other environment setup ...
    
    # Disable telemetry for Claude Code
    # This ensures Claude Code doesn't send telemetry data during runtime
    clean_env["DISABLE_TELEMETRY"] = "1"
    
    return clean_env
```

## Verification

You can verify that telemetry is disabled by:

1. **Running the test script**:
   ```bash
   python scripts/test_telemetry_env.py
   ```

2. **Running the unit tests**:
   ```bash
   python -m pytest tests/test_telemetry_disabled.py -v
   ```

3. **Checking the environment in a Claude session**:
   ```bash
   claude-mpm run --non-interactive -i "echo \$DISABLE_TELEMETRY"
   ```

## Scope

This setting affects:
- ✅ Claude Code launched via `claude-mpm run`
- ✅ Both interactive and non-interactive modes
- ✅ Both exec and subprocess launch methods
- ✅ All processes spawned by Claude Code

This setting does NOT affect:
- ❌ The claude-mpm CLI itself
- ❌ MCP servers (they have their own telemetry settings)
- ❌ Other wrapper scripts not specifically for Claude Code
- ❌ Direct invocations of Claude CLI outside of claude-mpm

## User Override

If for any reason a user needs to enable telemetry, they can:

1. Set the environment variable before running claude-mpm:
   ```bash
   DISABLE_TELEMETRY=0 claude-mpm run
   ```
   Note: This won't work as our code always sets it to "1"

2. Modify the source code to remove or change the setting

## Future Considerations

- Could add a CLI flag like `--enable-telemetry` if users need control
- Could make this configurable via the claude-mpm configuration file
- Currently hardcoded to always disable telemetry for maximum privacy