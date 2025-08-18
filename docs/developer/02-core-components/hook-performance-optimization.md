# Hook Performance Optimization

This document describes the performance optimizations implemented in the Claude MPM hook system to ensure minimal overhead in podcode processing operations.

## Overview

The hook system has been redesigned to be fully asynchronous with minimal overhead, addressing the previous synchronous bottlenecks that could slow down operations by up to 10 seconds per tool execution.

## Performance Improvements

### 1. Asynchronous Hook Processing

**Before**: Each hook triggered a synchronous `subprocess.run()` call that blocked the main thread for up to 5 seconds.

**After**: Hooks are queued for background processing with zero blocking time on the main thread.

```python
# Old synchronous approach (BLOCKING)
result = subprocess.run(
    ["python", hook_handler_path],
    input=event_json,
    timeout=5,  # Blocks main thread for up to 5 seconds
    capture_output=True
)

# New asynchronous approach (NON-BLOCKING)
self.hook_queue.put_nowait(hook_data)  # ~0.001 seconds
# Background thread processes hooks independently
```

### 2. Background Queue Processing

Hooks are now processed in a dedicated background thread:

- **Queue Size**: Configurable (default: 1000 hooks)
- **Processing**: Dedicated daemon thread
- **Timeout**: Configurable per hook (default: 2 seconds)
- **Failure Handling**: Graceful degradation without affecting main operations

### 3. Performance Mode

Complete hook disabling for maximum performance:

```bash
# Disable all hooks for critical operations
export CLAUDE_MPM_PERFORMANCE_MODE=true

# Selective hook disabling
export CLAUDE_MPM_HOOKS_PRE_TOOL=false
export CLAUDE_MPM_HOOKS_POST_TOOL=false
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_MPM_PERFORMANCE_MODE` | `false` | Disable all hooks for maximum performance |
| `CLAUDE_MPM_HOOKS_PRE_TOOL` | `true` | Enable/disable pre-tool hooks |
| `CLAUDE_MPM_HOOKS_POST_TOOL` | `true` | Enable/disable post-tool hooks |
| `CLAUDE_MPM_HOOKS_USER_PROMPT` | `true` | Enable/disable user prompt hooks |
| `CLAUDE_MPM_HOOKS_DELEGATION` | `true` | Enable/disable delegation hooks |
| `CLAUDE_MPM_HOOK_QUEUE_SIZE` | `1000` | Maximum hooks in background queue |
| `CLAUDE_MPM_HOOK_BG_TIMEOUT` | `2.0` | Background processing timeout (seconds) |

### Programmatic Configuration

```python
from claude_mpm.core.hook_performance_config import set_performance_mode

# Enable performance mode programmatically
set_performance_mode(True)

# Check current configuration
from claude_mpm.core.hook_performance_config import get_hook_performance_config
config = get_hook_performance_config()
print(config.print_config())
```

## Performance Metrics

### Before Optimization

- **Hook Timeout**: 5 seconds per hook
- **Tool Operation**: 2 hooks (pre + post) = 10 seconds blocking
- **100 Tool Operations**: 1000 seconds = ~17 minutes of blocking time
- **Subprocess Overhead**: Process creation/destruction for each hook

### After Optimization

- **Hook Queuing**: ~0.001 seconds per hook
- **Tool Operation**: ~0.002 seconds total overhead
- **100 Tool Operations**: ~0.2 seconds total overhead
- **Performance Improvement**: **5000x faster** for main thread operations

## Testing Performance

Use the provided test script to measure performance:

```bash
python scripts/test_hook_performance.py
```

This script will:
1. Test hook performance in different modes
2. Show configuration options
3. Benchmark against the old synchronous approach

## Implementation Details

### Background Thread Architecture

```python
class HookManager:
    def __init__(self):
        self.hook_queue = queue.Queue(maxsize=1000)
        self.background_thread = threading.Thread(
            target=self._process_hooks,
            daemon=True
        )
        self.background_thread.start()
    
    def _process_hooks(self):
        """Background thread processes hooks asynchronously."""
        while not self.shutdown_event.is_set():
            try:
                hook_data = self.hook_queue.get(timeout=1.0)
                self._execute_hook_sync(hook_data)
            except queue.Empty:
                continue
```

### Graceful Shutdown

The system includes proper cleanup mechanisms:

```python
def shutdown(self):
    """Shutdown background processing gracefully."""
    self.shutdown_event.set()
    self.hook_queue.put_nowait(None)  # Shutdown signal
    self.background_thread.join(timeout=2.0)
```

### Error Handling

- **Queue Full**: Hooks are dropped with warning (prevents memory issues)
- **Hook Failures**: Logged but don't affect main operations
- **Timeout**: Background hooks timeout independently
- **Shutdown**: Graceful cleanup on application exit

## Best Practices

### For Maximum Performance

1. **Enable Performance Mode** for critical operations:
   ```bash
   export CLAUDE_MPM_PERFORMANCE_MODE=true
   ```

2. **Selective Disabling** for specific hook types:
   ```bash
   export CLAUDE_MPM_HOOKS_PRE_TOOL=false
   ```

3. **Adjust Queue Size** based on memory constraints:
   ```bash
   export CLAUDE_MPM_HOOK_QUEUE_SIZE=500
   ```

### For Development/Debugging

1. **Keep Hooks Enabled** for full functionality
2. **Monitor Queue Size** to prevent memory issues
3. **Check Hook Logs** for debugging information

## Migration Guide

### Existing Code

No changes required for existing code. The hook manager API remains the same:

```python
# This code works unchanged
hook_manager = get_hook_manager()
hook_manager.trigger_pre_tool_hook("MyTool", {"arg": "value"})
hook_manager.trigger_post_tool_hook("MyTool", 0, "result")
```

### New Features

Take advantage of new configuration options:

```python
from claude_mpm.core.hook_performance_config import get_hook_performance_config

config = get_hook_performance_config()
if config.performance_mode:
    print("Running in high-performance mode")
```

## Monitoring

### Queue Health

Monitor hook queue status:

```python
hook_manager = get_hook_manager()
queue_size = hook_manager.hook_queue.qsize()
if queue_size > 800:  # Near capacity
    print(f"Warning: Hook queue at {queue_size}/1000 capacity")
```

### Performance Metrics

The system logs performance information:

```
DEBUG: Successfully queued PreToolUse hook for background processing
DEBUG: Hook PostToolUse processed in background thread (took 0.15s)
```

## Future Enhancements

### Planned Features

1. **Hook Batching**: Process multiple hooks in single subprocess call
2. **Metrics Collection**: Detailed performance metrics and monitoring
3. **Dynamic Configuration**: Runtime configuration changes
4. **Hook Prioritization**: Priority queues for critical hooks

### Experimental Features

Enable experimental batching:

```bash
export CLAUDE_MPM_HOOK_BATCHING=true
export CLAUDE_MPM_HOOK_BATCH_SIZE=10
export CLAUDE_MPM_HOOK_BATCH_TIMEOUT_MS=100
```

## Troubleshooting

### Common Issues

1. **Hooks Not Processing**: Check if performance mode is enabled
2. **Queue Full Warnings**: Increase queue size or reduce hook frequency
3. **Background Thread Issues**: Check logs for thread startup errors

### Debug Mode

Enable detailed logging:

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

This provides detailed information about hook processing, queue status, and performance metrics.
