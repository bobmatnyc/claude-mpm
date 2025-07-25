# Hook System Update: JSON-RPC Implementation

## Overview

The claude-mpm hook system has been updated to use JSON-RPC subprocess calls instead of HTTP servers. This change eliminates port exhaustion issues and simplifies deployment.

## What Changed

### Before (HTTP-based)
- Each claude-mpm instance spawned a Flask HTTP server
- Servers used ports 8080-8099, causing exhaustion
- Complex lifecycle management
- Resource intensive

### After (JSON-RPC-based)
- Hooks run as short-lived subprocesses
- Communication via stdin/stdout using JSON-RPC 2.0
- No ports needed
- Simple and efficient

## Migration

### Automatic
The system uses JSON-RPC hooks by default. No action needed for most users.

### Manual Migration
Run the migration script:
```bash
./scripts/migrate_to_json_rpc_hooks.py
```

### Reverting (not recommended)
To use the old HTTP system:
```bash
export CLAUDE_MPM_HOOKS_JSON_RPC=false
```

## Code Changes

### New Files
- `src/claude_mpm/hooks/json_rpc_executor.py` - Subprocess executor
- `src/claude_mpm/hooks/json_rpc_hook_client.py` - JSON-RPC client
- `src/claude_mpm/hooks/hook_runner.py` - Subprocess entry point
- `tests/test_json_rpc_hooks.py` - Comprehensive tests

### Modified Files
- `src/claude_mpm/hooks/hook_client.py` - Updated to use JSON-RPC by default
- `src/claude_mpm/hooks/builtin/*.py` - Fixed import paths

## Benefits

1. **No Port Exhaustion**: Eliminates the 8080-8099 port limit
2. **Better Performance**: No HTTP overhead
3. **Simpler Deployment**: No server management
4. **Process Isolation**: Each hook runs in its own process
5. **Backward Compatible**: Same API, different implementation

## Testing

Run the test suite:
```bash
python -m pytest tests/test_json_rpc_hooks.py -v
```

Run the demo:
```bash
./examples/json_rpc_hooks_demo.py
```

## Documentation

See `docs/json_rpc_hooks.md` for detailed documentation.