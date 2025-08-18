# Subprocess Utilities Migration Guide

This guide helps developers migrate from direct subprocess usage to the new unified utilities in Claude MPM.

## Overview

The subprocess improvements introduce two main utility modules:
- `claude_mpm.utils.subprocess_utils` - Subprocess execution and management
- `claude_mpm.utils.file_utils` - Safe file operations

These utilities provide:
- 🔒 Consistent error handling
- ⚡ Better performance through async support
- 🛡️ Enhanced reliability with process cleanup
- 📊 Built-in resource monitoring
- 🔄 Atomic file operations

## Quick Start

### Basic Subprocess Execution

```python
# Old way
import subprocess
result = subprocess.run(["echo", "Hello"], capture_output=True, text=True)

# New way
from claude_mpm.utils.subprocess_utils import run_subprocess
result = run_subprocess(["echo", "Hello"], capture_output=True)
```

### Async Subprocess Execution

```python
# Old way
proc = await asyncio.create_subprocess_exec("echo", "Hello", stdout=subprocess.PIPE)
stdout, _ = await proc.communicate()

# New way
from claude_mpm.utils.subprocess_utils import run_subprocess_async
result = await run_subprocess_async(["echo", "Hello"], capture_output=True)
```

## Migration Patterns

### 1. Error Handling

**Before:**
```python
try:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
except subprocess.CalledProcessError as e:
    logger.error(f"Command failed: {e}")
    logger.error(f"stderr: {e.stderr}")
except FileNotFoundError:
    logger.error("Command not found")
```

**After:**
```python
from claude_mpm.utils.subprocess_utils import run_subprocess, SubprocessError

try:
    result = run_subprocess(cmd, check=True, capture_output=True)
except SubprocessError as e:
    # All subprocess errors are wrapped in SubprocessError
    logger.error(f"Subprocess failed: {e}")
```

### 2. Timeout Handling

**Before:**
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError()

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(30)
try:
    result = subprocess.run(cmd)
finally:
    signal.alarm(0)
```

**After:**
```python
# Sync with timeout
result = run_subprocess(cmd, timeout=30)

# Async with timeout
result = await run_subprocess_async(cmd, timeout=30)
```

### 3. Process Tree Management

**Before:**
```python
# Complex platform-specific code to kill process trees
import psutil
parent = psutil.Process(pid)
for child in parent.children(recursive=True):
    child.kill()
parent.kill()
```

**After:**
```python
from claude_mpm.utils.subprocess_utils import terminate_process_tree

# Terminates entire process tree
terminated_count = terminate_process_tree(pid)
```

### 4. Process Cleanup and Orphan Management

**Before:**
```python
# Manual process cleanup - error-prone and platform-specific
import psutil
import time

def cleanup_old_processes():
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
        try:
            if 'my_script.py' in ' '.join(proc.info['cmdline']):
                age = time.time() - proc.info['create_time']
                if age > 3600:  # 1 hour
                    proc.terminate()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
```

**After:**
```python
from claude_mpm.utils.subprocess_utils import cleanup_orphaned_processes

# Clean up processes older than 1 hour
cleanup_count = cleanup_orphaned_processes('my_script.py', max_age_hours=1.0)
print(f"Cleaned up {cleanup_count} orphaned processes")
```

### 5. Working Directory and Environment

**Before:**
```python
import os
old_cwd = os.getcwd()
try:
    os.chdir(work_dir)
    result = subprocess.run(cmd, env={**os.environ, "KEY": "value"})
finally:
    os.chdir(old_cwd)
```

**After:**
```python
result = run_subprocess(
    cmd,
    cwd=work_dir,
    env={"KEY": "value"},  # Automatically merged with os.environ
)
```

### 5. File Operations

**Before:**
```python
# Risk of partial writes
with open(config_file, 'w') as f:
    json.dump(config, f)

# No error handling
with open(config_file, 'r') as f:
    config = json.load(f)
```

**After:**
```python
from claude_mpm.utils.file_utils import atomic_write, safe_read_file

# Atomic write - no corruption possible
atomic_write(config_file, json.dumps(config))

# Safe read with error handling
content = safe_read_file(config_file)
config = json.loads(content) if content else {}
```

## Common Migration Scenarios

### Migrating Hook Service

```python
# Before
class HookService:
    def _run_hook(self, hook_path, input_data):
        try:
            result = subprocess.run(
                [str(hook_path)],
                input=json.dumps(input_data),
                capture_output=True,
                text=True,
                timeout=30
            )
            # ... error handling ...
        except Exception as e:
            # ... complex error handling ...

# After
class HookService:
    def _run_hook(self, hook_path, input_data):
        result = run_subprocess(
            [str(hook_path)],
            input=json.dumps(input_data),
            capture_output=True,
            timeout=30
        )
        return json.loads(result.stdout) if result.stdout else None
```

### Migrating Agent Service

```python
# Before
async def create_agent_subprocess(self, agent_type, message):
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", "claude_mpm.agents.run_agent",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    # ... complex communication logic ...

# After  
async def create_agent_subprocess(self, agent_type, message):
    result = await run_subprocess_async(
        [sys.executable, "-m", "claude_mpm.agents.run_agent"],
        input=json.dumps({"type": agent_type, "message": message}),
        capture_output=True,
        timeout=300
    )
    return json.loads(result.stdout)
```

## Best Practices

### 1. Always Use Utilities for Subprocess Operations

```python
# ❌ Don't use subprocess directly
import subprocess
result = subprocess.run(...)

# ✅ Use utilities
from claude_mpm.utils.subprocess_utils import run_subprocess
result = run_subprocess(...)
```

### 2. Handle SubprocessError Appropriately

```python
from claude_mpm.utils.subprocess_utils import run_subprocess, SubprocessError

try:
    result = run_subprocess(cmd, check=True)
except SubprocessError as e:
    if "command not found" in str(e).lower():
        # Handle missing command
        logger.error(f"Required command not installed: {cmd[0]}")
    elif e.returncode == 1:
        # Handle specific error code
        logger.warning(f"Command failed with known error: {e}")
    else:
        # Handle other errors
        logger.error(f"Unexpected error: {e}")
        raise
```

### 3. Use Async for Long-Running Operations

```python
# For operations that might take time
result = await run_subprocess_async(
    ["npm", "install"],
    timeout=300,  # 5 minutes
    cwd=project_dir
)
```

### 4. Monitor Resource Usage

```python
from claude_mpm.utils.subprocess_utils import monitor_process_resources

# Start long-running process
proc = await asyncio.create_subprocess_exec(...)

# Monitor its resources
while proc.returncode is None:
    info = monitor_process_resources(proc.pid)
    if info and info['memory_mb'] > 1000:  # 1GB limit
        logger.warning(f"Process using too much memory: {info['memory_mb']}MB")
        terminate_process_tree(proc.pid)
        break
    await asyncio.sleep(1)
```

### 5. Use Atomic Operations for Critical Files

```python
from claude_mpm.utils.file_utils import atomic_write

# For configuration files, state files, etc.
config = {"version": "1.0", "settings": {...}}
atomic_write("config.json", json.dumps(config, indent=2))
```

## Performance Tips

### 1. Use Parallel Execution

```python
# Run multiple commands in parallel
import asyncio
from claude_mpm.utils.subprocess_utils import run_subprocess_async

commands = [
    ["npm", "test"],
    ["npm", "run", "lint"],
    ["npm", "run", "typecheck"]
]

# Run all commands in parallel
results = await asyncio.gather(
    *[run_subprocess_async(cmd, capture_output=True) for cmd in commands],
    return_exceptions=True
)
```

### 2. Reuse Environment Variables

```python
# Cache environment for multiple calls
base_env = {"NODE_ENV": "test", "CI": "true"}

for test_file in test_files:
    result = run_subprocess(
        ["npm", "test", test_file],
        env=base_env,  # Reused for each call
        capture_output=True
    )
```

## Troubleshooting

### Issue: Import Errors

```python
# Ensure you're importing from the correct module
from claude_mpm.utils.subprocess_utils import run_subprocess  # ✅
from utils.subprocess_utils import run_subprocess  # ❌ Wrong
```

### Issue: Timeout Not Working

```python
# Timeouts only work with run_subprocess (not with direct subprocess)
result = run_subprocess(cmd, timeout=30)  # ✅ Works
result = subprocess.run(cmd, timeout=30)  # ⚠️ Platform-dependent
```

### Issue: Process Not Terminating

```python
# Use terminate_process_tree for processes that spawn children
from claude_mpm.utils.subprocess_utils import terminate_process_tree

# This ensures all child processes are also terminated
terminate_process_tree(proc.pid)
```

## Module Reference

### subprocess_utils

- `run_subprocess()` - Synchronous subprocess execution with timeout and error handling
- `run_subprocess_async()` - Asynchronous subprocess execution with timeout support
- `SubprocessError` - Unified exception for subprocess errors with detailed context
- `SubprocessResult` - Result object with returncode, stdout, stderr, and success property
- `get_process_info()` - Get detailed process information including CPU, memory, and children
- `monitor_process_resources()` - Monitor process CPU/memory usage in real-time
- `terminate_process_tree()` - Gracefully terminate process and all children with timeout
- `cleanup_orphaned_processes()` - Clean up orphaned processes matching a pattern by age

### file_utils

- `ensure_directory()` - Create directory if it doesn't exist with proper error handling
- `safe_read_file()` - Read file with encoding support and error handling
- `safe_write_file()` - Write file with directory creation and encoding support
- `atomic_write()` - Atomic file write operation using temporary files
- `get_file_info()` - Get file metadata safely with size, timestamps, and permissions
- `safe_copy_file()` - Copy files with error handling and directory creation
- `safe_remove_file()` - Remove files safely with existence checking
- `read_json_file()` - Read and parse JSON files with error handling
- `write_json_file()` - Write JSON files with formatting and atomic write support
- `backup_file()` - Create backup copies of files with custom suffixes

## Hook Handler Process Fixes

The Claude MPM hook system has been enhanced to prevent process accumulation and improve reliability:

### Problem Solved

Previously, hook handler processes would accumulate due to:
- Blocking `sys.stdin.read()` calls that never received input
- Missing timeout protection causing infinite hangs
- Lack of proper cleanup mechanisms

### Improvements Made

1. **Non-blocking Input Reading**: Added `select()` with timeout to prevent hanging on stdin
2. **Process Timeout Protection**: 10-second timeout using `signal.alarm()`
3. **Enhanced Cleanup**: Signal handlers and atexit cleanup ensure proper termination
4. **Orphan Process Cleanup**: Automated cleanup script for monitoring and maintenance

### Usage

```python
# Monitor and clean up orphaned hook processes
from claude_mpm.utils.subprocess_utils import cleanup_orphaned_processes

# Clean up hook handlers older than 5 minutes
cleanup_count = cleanup_orphaned_processes('hook_handler.py', max_age_hours=5/60)
```

~~Or use the provided cleanup script~~ (Script removed during cleanup):

```bash
# Manual cleanup (replace removed script)
# Find and kill orphaned hook processes
ps aux | grep hook_handler.py | grep -v grep | awk '{print $2}' | xargs -r kill
```

## Next Steps

1. Review the demo scripts:
   - `demo/subprocess_improvements_demo.py` - Interactive demo
   - `demo/subprocess_before_after.py` - Before/after comparison

2. Monitor hook handler processes:
   - `scripts/cleanup_orphaned_hooks.py` - Process monitoring and cleanup

2. Start migrating modules that use subprocess heavily:
   - Hook service
   - Agent service  
   - MCP server service
   - Claude launcher

3. Run tests to ensure migrations work correctly:
   ```bash
   python -m pytest tests/utils/test_subprocess_utils.py
   python -m pytest tests/utils/test_file_utils.py
   ```

4. Monitor performance improvements using the built-in resource monitoring

For questions or issues, please refer to the inline documentation in the utility modules or create an issue in the project repository.