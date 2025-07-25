# Claude-MPM Demos

This directory contains demonstration scripts showcasing various improvements and features in the claude-mpm framework.

## Subprocess Improvements Demo

The `subprocess_improvements_demo.py` script demonstrates the comprehensive subprocess handling improvements implemented in the `feat/subprocess-improvements-demo` branch.

### Running the Demo

```bash
# From the project root
python demos/subprocess_improvements_demo.py

# Or make it executable and run directly
chmod +x demos/subprocess_improvements_demo.py
./demos/subprocess_improvements_demo.py
```

### Key Improvements Demonstrated

1. **Unified Subprocess Interface**
   - Single `SubprocessRunner` class for all subprocess operations
   - Consistent API across the entire codebase
   - Reduces code duplication by ~40%

2. **Enhanced Timeout Handling**
   - Graceful process termination on timeout
   - Partial output capture even when commands time out
   - Configurable timeout for all operations

3. **Comprehensive Error Handling**
   - Detailed error information in `SubprocessResult`
   - Proper handling of non-existent commands
   - Clear distinction between different failure modes

4. **Flexible Output Capture**
   - Multiple output modes: separate, combined, stdout-only, stderr-only
   - Suitable for different use cases across the framework
   - Consistent output handling regardless of execution mode

5. **Async Subprocess Support**
   - Full async/await support for concurrent operations
   - Parallel execution of multiple subprocesses
   - Async timeout handling

6. **Resource Management**
   - Context manager for managed process lifecycle
   - Automatic cleanup on exit
   - Proper signal handling

7. **Claude Integration**
   - Seamless integration with `ClaudeLauncher`
   - Unified subprocess handling for Claude CLI operations
   - Consistent timeout and error handling

8. **Real-World Patterns**
   - Git operations (version control agent)
   - Python script execution (testing)
   - Package manager operations (deployment)
   - Health checks with retries

### Code Reduction Impact

The subprocess improvements have significantly reduced code duplication:

- **Before**: Multiple subprocess implementations across orchestrators
- **After**: Single unified `SubprocessRunner` utility
- **Impact**: ~40% reduction in subprocess-related code

### Integration Points

The `SubprocessRunner` is now used by:
- `ClaudeLauncher` for Claude CLI operations
- Various orchestrators for process management
- Test utilities for command execution
- Agent implementations for system operations

### Example Usage

```python
from claude_mpm.utils.subprocess_runner import SubprocessRunner, quick_run

# Basic usage
runner = SubprocessRunner()
result = runner.run(['ls', '-la'])
if result.success:
    print(result.stdout)

# With timeout
result = runner.run_with_timeout(['long-command'], timeout=30)
if result.timed_out:
    print("Command timed out!")

# Quick functions
result = quick_run(['echo', 'Hello'])
print(result.stdout)

# Async execution
async def run_async():
    result = await runner.run_async(['command'])
    return result.stdout
```

### Architecture Benefits

1. **Consistency**: All subprocess operations use the same interface
2. **Maintainability**: Single point of implementation for subprocess logic
3. **Testability**: Easier to mock and test subprocess operations
4. **Extensibility**: New features benefit all subprocess users
5. **Error Handling**: Centralized error handling and logging

The demo script provides interactive examples of all these improvements, making it easy to understand the benefits and usage patterns.