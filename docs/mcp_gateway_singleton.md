# MCP Gateway Coordination Implementation

## Overview

The MCP Gateway implements a coordination pattern to ensure only one gateway handler is active per claude-mpm installation when invoked by MCP clients. Unlike background services, MCP gateways are stdio-based protocol handlers that are activated on-demand by Claude Desktop or other MCP clients.

## Architecture

### Global Gateway Manager

The `MCPGatewayManager` class provides:

- **Singleton Pattern**: Only one manager instance per process
- **File-based Locking**: Coordinates across multiple processes
- **Instance Tracking**: Monitors running gateway state
- **Clean Shutdown**: Proper resource cleanup

### Key Components

```
~/.claude-mpm/mcp/
├── gateway.lock     # Process lock file
└── gateway.json     # Instance metadata
```

## Implementation Details

### 1. Singleton Manager

```python
class MCPGatewayManager:
    _instance: Optional['MCPGatewayManager'] = None
    _lock = Lock()
    
    def __new__(cls):
        """Singleton pattern implementation."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
```

### 2. File-based Locking

- Uses `fcntl.flock()` for exclusive process locking
- Prevents multiple gateway instances across processes
- Automatic cleanup on process termination

### 3. Instance Coordination

```python
def get_running_instance_info() -> Optional[Dict[str, Any]]:
    """Get information about running gateway instance."""
    # Checks PID validity and returns instance metadata
```

### 4. Global Functions

```python
async def start_global_gateway(gateway_name: str, version: str) -> bool:
    """Start the global MCP gateway instance."""

async def run_global_gateway():
    """Run the global MCP gateway."""

def is_gateway_running() -> bool:
    """Check if gateway is currently running."""

def get_gateway_status() -> Optional[Dict[str, Any]]:
    """Get status of running gateway instance."""
```

## Usage Patterns

### CLI Integration

The CLI now uses the global manager:

```python
# Check if already running
if is_gateway_running():
    status = get_gateway_status()
    print(f"Gateway already running (PID: {status.get('pid')})")
    return 0

# Start global instance
if not await start_global_gateway(gateway_name, version):
    print("Error: Failed to start gateway")
    return 1

# Run the gateway
await run_global_gateway()
```

### Status Display

```bash
$ claude-mpm mcp status

Gateway Status: ℹ️  MCP protocol handler (stdio-based)
  • Activated on-demand by MCP clients (Claude Desktop)
  • No background processes - communicates via stdin/stdout
  • Ready for Claude Desktop integration
  • Test with: claude-mpm mcp test <tool_name>
```

## Benefits

### 1. **Single Instance Guarantee**
- Only one gateway per installation
- Prevents resource conflicts
- Consistent behavior across projects

### 2. **Process Coordination**
- File-based locking works across processes
- Automatic cleanup on termination
- Proper error handling for lock failures

### 3. **Resource Management**
- Shared tool registry across invocations
- Efficient memory usage
- Clean shutdown procedures

### 4. **User Experience**
- Clear status reporting
- Predictable behavior
- Easy troubleshooting

## Comparison with Hooks Service

| Aspect | Hooks Service | MCP Gateway |
|--------|---------------|-------------|
| **Pattern** | Singleton class | Singleton manager |
| **Coordination** | In-process only | Cross-process locking |
| **State** | Memory-based | File-based tracking |
| **Lifecycle** | Event-driven | Long-running service |
| **Cleanup** | Automatic | Signal handlers + atexit |

## Error Handling

### Lock Acquisition Failure
```python
if not manager.acquire_lock():
    existing_info = manager.get_running_instance_info()
    if existing_info:
        print(f"Gateway already running (PID: {existing_info['pid']})")
    return False
```

### Stale Process Detection
```python
def get_running_instance_info():
    # Check if PID still exists
    try:
        os.kill(pid, 0)
        return info
    except ProcessLookupError:
        # Clean up stale files
        self.instance_file.unlink()
        return None
```

## Testing

### Singleton Behavior
```python
# Test that second instance fails gracefully
result1 = await start_global_gateway('gateway-1', '1.0.0')  # True
result2 = await start_global_gateway('gateway-2', '2.0.0')  # True (reuses existing)
```

### Status Verification
```python
assert is_gateway_running() == True
status = get_gateway_status()
assert status['gateway_name'] == 'gateway-1'
```

## Future Enhancements

1. **Health Monitoring**: Periodic health checks of running instance
2. **Graceful Restart**: Ability to restart gateway without losing state
3. **Multi-user Support**: Per-user gateway instances
4. **Configuration Sync**: Automatic config updates to running instance

## Migration Notes

- Existing functionality preserved
- CLI commands work unchanged
- Tool invocations remain compatible
- No breaking changes to public API

The singleton implementation ensures robust, predictable MCP gateway behavior while maintaining all existing functionality and improving resource management.
