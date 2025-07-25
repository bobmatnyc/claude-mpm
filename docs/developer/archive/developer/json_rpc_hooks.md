# JSON-RPC Hook System

This document describes the JSON-RPC based hook system that replaces the HTTP-based implementation in claude-mpm.

## Overview

The JSON-RPC hook system executes hooks as subprocess calls using JSON-RPC 2.0 protocol for communication. This eliminates the need for a persistent HTTP server and resolves port exhaustion issues.

### Key Benefits

1. **No Port Exhaustion**: No HTTP servers means no port allocation needed
2. **Resource Efficient**: Hooks run as short-lived subprocesses
3. **Simpler Lifecycle**: No server start/stop management
4. **Better Isolation**: Each hook runs in its own process
5. **Backward Compatible**: Maintains the same hook interface

## Architecture

```
┌─────────────────┐     JSON-RPC      ┌──────────────────┐
│   Hook Client   │ ◀─────────────────▶│  Hook Executor   │
│                 │    via stdin/out    │                  │
└─────────────────┘                    └──────────────────┘
                                               │
                                               │ subprocess
                                               ▼
                                       ┌──────────────────┐
                                       │   Hook Runner    │
                                       │  (subprocess)    │
                                       └──────────────────┘
                                               │
                                               │ loads
                                               ▼
                                       ┌──────────────────┐
                                       │   Hook Classes   │
                                       │   (builtin/)     │
                                       └──────────────────┘
```

## Components

### JSONRPCHookClient (`json_rpc_hook_client.py`)

The client interface that applications use to execute hooks. It:
- Discovers available hooks from the builtin directory
- Provides the same interface as the HTTP-based client
- Delegates execution to JSONRPCHookExecutor

### JSONRPCHookExecutor (`json_rpc_executor.py`)

Handles the subprocess execution and JSON-RPC communication:
- Spawns hook_runner.py as a subprocess
- Sends JSON-RPC requests via stdin
- Receives JSON-RPC responses via stdout
- Handles timeouts and errors

### Hook Runner (`hook_runner.py`)

The subprocess entry point that:
- Reads JSON-RPC requests from stdin
- Loads and executes the requested hook
- Returns JSON-RPC responses to stdout
- Supports both single and batch requests

## Usage

### Basic Usage

```python
from claude_mpm.hooks.hook_client import get_hook_client

# Get a hook client (returns JSONRPCHookClient by default)
client = get_hook_client()

# Execute submit hooks
results = client.execute_submit_hook("Fix TSK-123 urgently")

# Process results
for result in results:
    if result['success']:
        print(f"Hook {result['hook_name']} executed successfully")
        if result.get('modified'):
            print(f"Data modified: {result['data']}")
```

### Environment Variables

- `CLAUDE_MPM_HOOKS_JSON_RPC`: Set to "false" to use legacy HTTP client (default: "true")

### Creating Custom Hooks

Custom hooks work exactly the same as before. Create a class inheriting from one of the base hook types:

```python
from claude_mpm.hooks.base_hook import SubmitHook, HookContext, HookResult

class MyCustomHook(SubmitHook):
    def __init__(self):
        super().__init__(name="my_custom_hook", priority=50)
        
    def execute(self, context: HookContext) -> HookResult:
        prompt = context.data.get('prompt', '')
        
        # Process the prompt
        processed_data = {"processed_prompt": prompt.upper()}
        
        return HookResult(
            success=True,
            data=processed_data,
            modified=True
        )
```

Place your hook in `src/claude_mpm/hooks/builtin/` and it will be automatically discovered.

## JSON-RPC Protocol

### Request Format

```json
{
    "jsonrpc": "2.0",
    "method": "execute_hook",
    "params": {
        "hook_name": "ticket_detection",
        "hook_type": "submit",
        "context_data": {
            "prompt": "Fix TSK-123"
        },
        "metadata": {}
    },
    "id": "unique_request_id"
}
```

### Response Format (Success)

```json
{
    "jsonrpc": "2.0",
    "result": {
        "hook_name": "ticket_detection",
        "success": true,
        "data": {
            "tickets": ["TSK-123"],
            "prompt": "Fix TSK-123"
        },
        "modified": true,
        "metadata": {"ticket_count": 1},
        "execution_time_ms": 12.5
    },
    "id": "unique_request_id"
}
```

### Response Format (Error)

```json
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32602,
        "message": "Invalid params",
        "data": "Hook 'unknown_hook' not found"
    },
    "id": "unique_request_id"
}
```

### Error Codes

- `-32700`: Parse error (invalid JSON)
- `-32600`: Invalid request
- `-32601`: Method not found
- `-32602`: Invalid params
- `-32603`: Internal error

## Migration Guide

### For Users

No changes needed! The system automatically uses JSON-RPC hooks by default. To use the legacy HTTP system:

```bash
export CLAUDE_MPM_HOOKS_JSON_RPC=false
```

### For Developers

The hook interface remains the same. If you have custom code that directly uses `HookServiceClient`, it will continue to work but will use JSON-RPC under the hood.

To explicitly use the JSON-RPC client:

```python
from claude_mpm.hooks.json_rpc_hook_client import JSONRPCHookClient

client = JSONRPCHookClient()
# Use client as before
```

## Performance Considerations

1. **Startup Overhead**: Each hook execution spawns a subprocess, adding ~50-100ms overhead
2. **Batch Processing**: Use batch execution for multiple hooks to amortize startup cost
3. **Hook Discovery**: Happens once at client initialization, not per execution
4. **Timeouts**: Default 30s timeout, configurable per client

## Troubleshooting

### Hook Not Found

```python
# Check discovered hooks
client = JSONRPCHookClient()
health = client.health_check()
print(f"Discovered hooks: {health['discovered_hooks']}")
```

### Debugging Hook Execution

Hook runner logs to stderr, which doesn't interfere with JSON-RPC communication:

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Testing Hooks

Run the hook runner directly for testing:

```bash
echo '{"jsonrpc":"2.0","method":"execute_hook","params":{"hook_name":"ticket_detection","hook_type":"submit","context_data":{"prompt":"TSK-123"}},"id":"test"}' | python src/claude_mpm/hooks/hook_runner.py
```

## Future Enhancements

1. **Hook Caching**: Cache hook instances between executions
2. **Async Support**: Native async/await support for hook execution
3. **Plugin System**: Load hooks from external packages
4. **Performance Monitoring**: Built-in metrics for hook execution