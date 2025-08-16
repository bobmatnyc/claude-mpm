# Hook System Troubleshooting

This guide helps troubleshoot common issues with the Claude MPM hook system.

## Common Issues

### 1. Orphaned Hook Processes

**Symptoms:**
- High CPU usage from multiple `hook_handler.py` processes
- Slow system performance
- Many processes in `ps aux | grep hook_handler`

**Diagnosis:**
```bash
# Check for orphaned hook processes
ps aux | grep hook_handler.py | grep -v grep | wc -l

# Show process details
ps aux | grep hook_handler.py | grep -v grep
```

**Solution:**
```bash
# Use the cleanup script
python scripts/cleanup_orphaned_hooks.py

# Or clean up programmatically
python -c "
import sys
sys.path.insert(0, 'src')
from claude_mpm.utils.subprocess_utils import cleanup_orphaned_processes
count = cleanup_orphaned_processes('hook_handler.py', max_age_hours=0.1)
print(f'Cleaned up {count} processes')
"
```

**Prevention:**
- The hook system now includes automatic timeout protection
- Processes should self-terminate after 10 seconds
- Regular monitoring with the cleanup script

### 2. Hook Handler Timeouts

**Symptoms:**
- Hook events not processing
- "Hook handler timeout" messages in logs
- Hooks appearing to hang

**Diagnosis:**
```bash
# Check for hanging processes
lsof -p <hook_process_pid>

# Monitor process activity
top -p <hook_process_pid>
```

**Solution:**
- Hook handlers now have built-in 10-second timeouts
- Processes automatically terminate if they hang
- Check for blocking operations in custom hooks

**Best Practices:**
- Avoid blocking I/O operations in hooks
- Use async operations for network calls
- Keep hook logic lightweight and fast

### 3. Socket.IO Connection Issues

**Symptoms:**
- Hooks not receiving events
- Connection refused errors
- Socket.IO server not responding

**Diagnosis:**
```bash
# Check if Socket.IO server is running
netstat -an | grep 8765

# Test connection
curl -I http://localhost:8765/socket.io/
```

**Solution:**
```bash
# Restart the Socket.IO server
claude-mpm hooks restart

# Check server logs
claude-mpm hooks logs
```

### 4. Hook Registration Failures

**Symptoms:**
- Custom hooks not executing
- "Hook not found" errors
- Hooks not appearing in registry

**Diagnosis:**
```python
# Check hook registry
from claude_mpm.hooks.registry import HookRegistry
registry = HookRegistry()
print(registry.list_hooks())
```

**Solution:**
- Ensure hooks are properly registered
- Check hook file permissions
- Verify hook syntax and imports

## Monitoring and Maintenance

### Regular Cleanup

Add this to your cron jobs for automatic cleanup:

```bash
# Clean up orphaned hook processes every 15 minutes
*/15 * * * * /path/to/python /path/to/claude-mpm/scripts/cleanup_orphaned_hooks.py
```

### Process Monitoring

Monitor hook process health:

```python
from claude_mpm.utils.subprocess_utils import get_process_info, monitor_process_resources
import psutil

# Monitor all hook processes
for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
    if 'hook_handler.py' in ' '.join(proc.info['cmdline'] or []):
        info = monitor_process_resources(proc.info['pid'])
        if info and info['memory_mb'] > 100:  # Alert if using >100MB
            print(f"High memory usage: PID {proc.info['pid']} using {info['memory_mb']:.1f}MB")
```

### Log Analysis

Check hook system logs:

```bash
# View recent hook activity
tail -f ~/.claude-mpm/logs/hooks.log

# Search for errors
grep -i error ~/.claude-mpm/logs/hooks.log

# Check for timeout issues
grep -i timeout ~/.claude-mpm/logs/hooks.log
```

## Performance Optimization

### Hook Performance Tips

1. **Keep hooks lightweight**: Avoid heavy computations
2. **Use async operations**: For I/O bound tasks
3. **Implement caching**: For expensive operations
4. **Monitor resource usage**: Regular cleanup and monitoring

### Resource Limits

Set resource limits for hook processes:

```python
import resource

# Limit memory usage (100MB)
resource.setrlimit(resource.RLIMIT_AS, (100 * 1024 * 1024, -1))

# Limit CPU time (30 seconds)
resource.setrlimit(resource.RLIMIT_CPU, (30, -1))
```

## Advanced Debugging

### Debug Mode

Enable debug mode for detailed logging:

```bash
export CLAUDE_MPM_DEBUG=1
claude-mpm run
```

### Process Tracing

Trace hook process execution:

```bash
# On macOS
sudo dtruss -p <hook_process_pid>

# On Linux
sudo strace -p <hook_process_pid>
```

### Memory Analysis

Analyze memory usage:

```python
import tracemalloc
import psutil

# Start memory tracing
tracemalloc.start()

# Your hook code here

# Get memory statistics
current, peak = tracemalloc.get_traced_memory()
print(f"Current memory usage: {current / 1024 / 1024:.1f}MB")
print(f"Peak memory usage: {peak / 1024 / 1024:.1f}MB")
```

## Getting Help

If you continue to experience issues:

1. **Check the logs**: `~/.claude-mpm/logs/hooks.log`
2. **Run diagnostics**: `python scripts/cleanup_orphaned_hooks.py`
3. **File an issue**: Include process list, logs, and system info
4. **Community support**: Check the documentation and forums

## Related Documentation

- [Hook System Architecture](../developer/02-core-components/hook-system.md)
- [Subprocess Migration Guide](../developer/06-internals/migrations/subprocess_migration_guide.md)
- [Process Management Best Practices](../developer/06-internals/process-management.md)
