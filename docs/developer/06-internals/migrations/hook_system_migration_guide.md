# Hook System Migration Guide: HTTP to JSON-RPC

## Overview

This guide documents the migration from the HTTP-based hook system to the JSON-RPC implementation in claude-mpm. The JSON-RPC implementation offers better performance and reliability by eliminating the need for an HTTP server.

## Key Differences

### HTTP-based Hook System
- Required running an HTTP server (port 5001 by default)
- Used `HookServiceClient` class from `claude_mpm.hooks.hook_client`
- Network-based communication with retry logic
- Required service startup/shutdown management

### JSON-RPC Hook System
- No server required - direct subprocess execution
- Uses `JSONRPCHookClient` class from `claude_mpm.hooks.json_rpc_hook_client`
- Direct process communication with better error handling
- Automatic hook discovery from builtin directory

## Migration Steps

### 1. Update Imports

**Before:**
```python
from claude_mpm.hooks.hook_client import HookServiceClient, get_hook_client
```

**After:**
```python
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient, get_hook_client
```

### 2. Update Client Initialization

**Before:**
```python
# Initialize with base URL
client = HookServiceClient(base_url="http://localhost:5001")

# Or use convenience function
client = get_hook_client()
```

**After:**
```python
# Initialize directly (no URL needed)
client = JSONRPCHookClient()

# Or use convenience function (compatible)
client = get_hook_client()
```

### 3. Update Hook Manager Usage

**Before:**
```python
# HTTP-based hook manager (if it existed)
hook_manager = HTTPHookManager()
hook_manager.start_service(port=5001)
```

**After:**
```python
from claude_mpm.services.json_rpc_hook_manager import JSONRPCHookManager

hook_manager = JSONRPCHookManager()
hook_manager.start_service()  # No port needed
```

## API Compatibility

The JSON-RPC client maintains full API compatibility with the HTTP client:

- `health_check()` - Check system health
- `list_hooks()` - List available hooks
- `execute_hook()` - Execute hooks by type
- `execute_submit_hook()` - Execute submit hooks
- `execute_pre_delegation_hook()` - Execute pre-delegation hooks
- `execute_post_delegation_hook()` - Execute post-delegation hooks
- `execute_ticket_extraction_hook()` - Execute ticket extraction hooks
- `get_modified_data()` - Extract modified data from results
- `get_extracted_tickets()` - Extract tickets from results

## Behavioral Differences

1. **Hook Discovery**: JSON-RPC automatically discovers hooks from the `builtin` directory
2. **Error Handling**: JSON-RPC provides more detailed error information through `JSONRPCError`
3. **Performance**: JSON-RPC is faster due to no network overhead
4. **Configuration**: No need for port configuration or URL management

## Environment Variables

The HTTP client used: `CLAUDE_MPM_HOOKS_URL`
The JSON-RPC client ignores this variable.

## Testing

Update your tests to use the JSON-RPC client:

```python
import unittest
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient

class TestHooks(unittest.TestCase):
    def setUp(self):
        self.client = JSONRPCHookClient()
    
    def test_hook_execution(self):
        results = self.client.execute_submit_hook("test prompt")
        self.assertIsInstance(results, list)
```

## Deprecation Timeline

- **Current**: HTTP client deprecated, JSON-RPC is default
- **Next Release**: HTTP client will show deprecation warnings
- **Future Release**: HTTP client will be removed

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure you're importing from `json_rpc_hook_client`
2. **Missing Hooks**: Check that hook files are in the `builtin` directory
3. **Execution Errors**: Check subprocess permissions and Python path

### Debug Mode

Enable debug logging to see hook execution details:
```python
import logging
logging.getLogger("claude_mpm.hooks").setLevel(logging.DEBUG)
```

## Support

For questions or issues with the migration, please refer to:
- GitHub Issues: [claude-mpm repository]
- Documentation: `/docs/developer/02-core-components/hook-system.md`