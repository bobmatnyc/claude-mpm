# Claude MPM Internals

This section provides deep technical documentation about the internal workings of Claude MPM.

## Overview

This documentation is intended for:
- Core contributors
- Advanced users who need to understand internals
- Developers debugging complex issues
- Those interested in the architecture decisions

## Contents

### [Subprocess Logging](subprocess-logging.md)
Detailed documentation on how subprocess output is captured, processed, and logged throughout the system.

### [Migrations](migrations/)
Historical migration guides showing how the codebase has evolved:
- [Subprocess Migration Guide](migrations/subprocess-migration-guide.md) - Migration from multiple subprocess implementations to unified approach
- [Claude Launcher Migration](migrations/claude-launcher-migration.md) - Introduction of the centralized launcher
- [Logger Mixin Migration](migrations/logger-mixin-migration.md) - Standardization of logging across components
- [Path Resolver Migration](migrations/path-resolver-migration.md) - Unified path resolution strategy

### [Analysis](analysis/)
In-depth codebase analysis and technical reports:
- [Codebase Analysis](analysis/codebase-analysis.md) - Comprehensive analysis of code structure
- [Tree-sitter Analysis](analysis/tree-sitter-analysis.md) - AST-based code analysis results
- [Code Visualizations](analysis/code-visualizations.md) - Visual representations of the codebase

## Key Internal Concepts

### 1. Process Management

Claude MPM uses subprocess.Popen to manage Claude processes:

```python
# Core pattern used throughout
process = subprocess.Popen(
    cmd,
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

### 2. I/O Threading

Input and output are handled in separate threads to prevent blocking:

```python
# Output thread pattern
def _output_reader(self):
    while self.running:
        line = self.process.stdout.readline()
        if line:
            self._process_output_line(line)
```

### 3. Framework Injection

The framework is injected on first interaction:

```python
if self.first_interaction:
    framework = self.framework_loader.get_framework_instructions()
    full_input = framework + "\n\nUser: " + user_input
    self.first_interaction = False
```

### 4. Ticket Extraction

Pattern matching is used to extract tickets from Claude's output:

```python
# Patterns like [TASK], [BUG], [FEATURE]
patterns = [
    r'\[TASK\]\s*(.+)',
    r'\[BUG\]\s*(.+)',
    r'\[FEATURE\]\s*(.+)'
]
```

### 5. Hook Execution

Hooks are executed asynchronously with proper error handling:

```python
async def execute_hooks(hook_type, context):
    results = []
    for hook in get_hooks(hook_type):
        try:
            result = await hook.execute(context)
            results.append(result)
        except Exception as e:
            # Handle gracefully
            pass
    return results
```

## Architecture Decisions

### Why Subprocess over Direct API?

1. **Compatibility**: Works with the official Claude CLI
2. **Flexibility**: Can intercept and modify all I/O
3. **Control**: Full control over the execution environment
4. **Future-proof**: Can adapt to CLI changes

### Why Multiple Orchestrators?

1. **Different use cases**: Interactive vs batch processing
2. **Platform compatibility**: PTY vs pipes
3. **Performance**: Optimized for specific scenarios
4. **Extensibility**: Easy to add new strategies

### Why Hook System?

1. **Extensibility**: Add functionality without modifying core
2. **Separation of concerns**: Keep core logic clean
3. **Plugin support**: Enable third-party extensions
4. **Testability**: Hooks can be tested in isolation

## Performance Considerations

### Memory Usage

- Output buffering is limited to prevent memory issues
- Ticket extraction is done streaming, not batch
- Hook execution is async to prevent blocking

### CPU Usage

- Regex patterns are pre-compiled
- Output processing is done line-by-line
- Threading prevents CPU blocking

### I/O Efficiency

- Non-blocking I/O where possible
- Buffered reading for efficiency
- Selective logging to reduce disk I/O

## Security Considerations

### Process Isolation

- Each Claude instance runs in its own process
- No shared memory between sessions
- Clean process termination

### Input Validation

- User input is validated before processing
- Command injection is prevented
- Path traversal is blocked

### Output Sanitization

- ANSI codes are stripped when needed
- Sensitive information is filtered
- Logs are sanitized

## Debugging Internals

### Enable Debug Logging

```bash
export CLAUDE_MPM_LOG_LEVEL=DEBUG
claude-mpm --log-level DEBUG
```

### Trace Subprocess Execution

```python
# In your code
import logging
logging.getLogger("claude_mpm.subprocess").setLevel(logging.DEBUG)
```

### Monitor Hook Execution

```python
# Hook execution is logged
logger.debug(f"Executing hook: {hook.name}")
```

### Analyze Performance

```python
import cProfile
import pstats

# Profile orchestrator
pr = cProfile.Profile()
pr.enable()

orchestrator.run_interactive()

pr.disable()
stats = pstats.Stats(pr)
stats.sort_stats('cumulative')
stats.print_stats()
```

## Contributing to Internals

When modifying internal components:

1. **Understand the impact**: Changes affect the entire system
2. **Maintain compatibility**: Don't break existing functionality
3. **Add tests**: Especially for edge cases
4. **Document changes**: Update this documentation
5. **Consider performance**: Profile before and after
6. **Think about security**: Review for vulnerabilities

## Future Internals Work

Planned improvements to internals:

1. **Async subprocess**: Move to asyncio.subprocess
2. **Better streaming**: Improved output streaming
3. **Memory optimization**: Reduce memory footprint
4. **Performance monitoring**: Built-in profiling
5. **Plugin sandboxing**: Isolate plugin execution
6. **Caching layer**: Smart prompt/response caching

## Resources

- [Python subprocess documentation](https://docs.python.org/3/library/subprocess.html)
- [asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [Threading best practices](https://docs.python.org/3/library/threading.html)
- [Security considerations](https://docs.python.org/3/library/subprocess.html#security-considerations)