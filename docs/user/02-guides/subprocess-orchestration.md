# Subprocess Orchestration Guide

Learn how Claude MPM's subprocess orchestration provides advanced control and monitoring of Claude sessions.

## What is Subprocess Orchestration?

Subprocess orchestration runs Claude as a controlled child process, enabling:

- **Real-time monitoring** of inputs and outputs
- **Pattern detection** for tickets and delegations
- **Resource management** with memory and timeout limits
- **Parallel execution** of agent delegations
- **Session control** with start, stop, and restart capabilities

## Orchestration Modes

### 1. Standard Mode (Default)

Basic subprocess control with pattern detection:

```bash
# Runs Claude with standard orchestration
claude-mpm run -i "Create a web server" --non-interactive
```

Features:
- Framework injection
- Ticket extraction
- Basic logging

### 2. Interactive Subprocess Mode

Full subprocess control with parallel execution:

```bash
# Enable interactive subprocess orchestration
claude-mpm run --subprocess -i "Create a Python app with tests and docs"

# With logging
claude-mpm run --subprocess --logging INFO -i "Complex task"
```

Features:
- Parallel agent execution
- Memory monitoring
- Advanced logging
- Process management

### 3. Direct Mode

Minimal orchestration for interactive sessions:

```bash
# Standard interactive mode
claude-mpm
```

Claude handles its own I/O with minimal intervention.

## Parallel Agent Execution

### How It Works

When Claude delegates to multiple agents, subprocess orchestration can run them in parallel:

```
PM: "I'll delegate this to multiple agents..."
    ↓
Detected delegations:
- Engineer: Create server
- QA: Write tests  
- Docs: Generate documentation
    ↓
Running 3 parallel subprocesses...
```

### Example

```bash
claude-mpm run --subprocess -i "Create a REST API with authentication, comprehensive tests, and API documentation"
```

Output:
```
Detected 3 delegations. Running in parallel...

[✓] Engineer: Create REST API (3.2s)
[✓] QA: Write tests (2.8s)  
[✓] Documentation: Generate docs (2.1s)

Total time: 3.2s (parallel) vs 8.1s (sequential)
```

### Disable Parallel Execution

```bash
# Run delegations sequentially
claude-mpm run --subprocess --no-parallel -i "Complex task"
```

## Memory Management

### Memory Monitoring

Each subprocess has memory limits and monitoring:

```bash
# Default: 2GB limit per subprocess
claude-mpm run --subprocess -i "Memory-intensive task"

# Custom limit
claude-mpm run --subprocess --memory-limit 4096 -i "Large analysis"
```

### Memory Warnings

```
Warning: Process 'Engineer' memory usage at 1.5GB (75% of limit)
Critical: Process 'Engineer' approaching memory limit (1.9GB/2.0GB)
Error: Process 'Engineer' exceeded memory limit - terminating
```

### Configuration

Set per-agent memory limits in configuration:

```python
# In your config
AGENT_MEMORY_LIMITS = {
    "Engineer": 3072,      # 3GB for code generation
    "QA": 2048,           # 2GB for testing
    "Research": 4096,     # 4GB for analysis
    "Documentation": 1024  # 1GB for docs
}
```

## Process Management

### Timeouts

Prevent runaway processes:

```bash
# Default: 5 minute timeout
claude-mpm run --subprocess -i "Task"

# Custom timeout (10 minutes)
claude-mpm run --subprocess --timeout 600 -i "Long task"
```

### Process Control

The orchestrator manages process lifecycle:

1. **Creation**: Spawn Claude subprocess
2. **Monitoring**: Track resources and output
3. **Communication**: Send prompts, receive responses
4. **Termination**: Clean shutdown or force kill

### Active Process Monitoring

During execution, you can see:
- Process IDs
- Memory usage
- CPU usage
- Execution time
- Status

## Logging and Debugging

### Logging Levels

```bash
# No logging (default)
claude-mpm run --subprocess -i "Task"

# Info logging
claude-mpm run --subprocess --logging INFO -i "Task"

# Debug logging (verbose)
claude-mpm run --subprocess --logging DEBUG -i "Task"
```

### Log Output

```
[INFO] Starting subprocess orchestration
[INFO] Detected 3 delegations in PM response
[INFO] Creating subprocess for Engineer agent
[DEBUG] Process 12345: Memory 156MB, CPU 45%
[INFO] Engineer completed in 3.2s
```

### Log Files

Logs are saved to:
```
~/.claude-mpm/logs/
├── orchestration_20240125_143022.log
├── subprocess_engineer_12345.log
├── subprocess_qa_12346.log
└── subprocess_docs_12347.log
```

## Delegation Detection

### Patterns Detected

The orchestrator recognizes these delegation patterns:

```
**Agent Name**: Task description
[Agent] Task description
→ Agent: Task description
Delegate to Agent: Task description
```

### Example Delegations

```
# These will trigger parallel execution:
"**Engineer**: Implement the authentication system"
"**QA Agent**: Write comprehensive tests"
"Documentation → Create API reference"
```

### Custom Patterns

Configure additional patterns:

```python
DELEGATION_PATTERNS = [
    r'\*\*(\w+)\s*(?:Agent)?\*\*:\s*(.+)',
    r'→\s*(\w+):\s*(.+)',
    r'\[(\w+)\]\s*(.+)',
    # Add your patterns
]
```

## Advanced Configuration

### Subprocess Options

```python
# Configure subprocess behavior
SUBPROCESS_CONFIG = {
    "shell": False,              # Don't use shell
    "buffer_size": 8192,         # I/O buffer size
    "encoding": "utf-8",         # Text encoding
    "timeout": 300,              # Default timeout
    "memory_limit_mb": 2048,     # Default memory limit
    "parallel_enabled": True,     # Allow parallel execution
    "max_parallel": 5            # Max parallel processes
}
```

### Environment Variables

```bash
# Set subprocess environment
export CLAUDE_MPM_SUBPROCESS_TIMEOUT=600
export CLAUDE_MPM_MEMORY_LIMIT=4096
export CLAUDE_MPM_PARALLEL=true
```

## Use Cases

### 1. Complex Multi-Step Tasks

Perfect for tasks that need multiple specialists:

```bash
claude-mpm run --subprocess -i "Build a complete web application with user authentication, real-time chat, comprehensive test suite, and deployment configuration"
```

### 2. Performance Optimization

Run independent tasks in parallel:

```bash
claude-mpm run --subprocess -i "Analyze these 5 Python modules for performance issues and generate optimization reports for each"
```

### 3. Resource-Intensive Operations

Monitor and control memory usage:

```bash
claude-mpm run --subprocess --memory-limit 8192 -i "Process this large dataset and generate visualizations"
```

### 4. Automated Workflows

Chain commands with subprocess control:

```bash
#!/bin/bash
# Automated code review workflow

claude-mpm run --subprocess -i "Review architecture of src/" 
claude-mpm run --subprocess -i "Security audit of authentication"
claude-mpm run --subprocess -i "Performance analysis of API endpoints"
```

## Troubleshooting

### Common Issues

**"pexpect not found"**
```bash
pip install pexpect psutil
```

**"Process exceeded memory limit"**
```bash
# Increase limit
claude-mpm run --subprocess --memory-limit 4096 -i "Task"

# Or disable monitoring
claude-mpm run --subprocess --no-memory-monitoring -i "Task"
```

**"Timeout waiting for response"**
```bash
# Increase timeout
claude-mpm run --subprocess --timeout 900 -i "Complex task"
```

**"Delegation not detected"**
Ensure clear delegation syntax:
```
✓ **Engineer**: Create function
✗ Engineer create function
```

### Debug Mode

Enable detailed debugging:

```bash
# Maximum verbosity
claude-mpm run --subprocess --logging DEBUG --debug -i "Task"

# Save debug output
claude-mpm run --subprocess --logging DEBUG -i "Task" 2>&1 | tee debug.log
```

## Best Practices

### 1. Use for Complex Tasks

Subprocess orchestration shines with multi-agent tasks:

```bash
# Good use case
claude-mpm run --subprocess -i "Create a microservice with API, tests, docs, and deployment"

# Overkill for simple tasks
claude-mpm run --subprocess -i "What is 2+2?"  # Just use regular mode
```

### 2. Monitor Resource Usage

For resource-intensive tasks:

```bash
# Set appropriate limits
claude-mpm run --subprocess --memory-limit 4096 --timeout 600 -i "Large analysis task"
```

### 3. Enable Logging for Debugging

When things go wrong:

```bash
claude-mpm run --subprocess --logging DEBUG -i "Problematic task" --log-dir ./debug_logs
```

### 4. Use Parallel Execution Wisely

Parallel is faster but uses more resources:

```bash
# Good: Independent tasks
claude-mpm run --subprocess -i "Create 3 independent microservices"

# Bad: Dependent tasks (use --no-parallel)
claude-mpm run --subprocess --no-parallel -i "Create API, then tests based on API"
```

## Integration Examples

### CI/CD Integration

```yaml
# .github/workflows/code-review.yml
- name: Automated Code Review
  run: |
    claude-mpm run --subprocess --non-interactive \
      -i "Review code changes and create tickets for issues" \
      --timeout 600
```

### Git Hooks

```bash
#!/bin/bash
# .git/hooks/pre-push
claude-mpm run --subprocess --non-interactive \
  -i "Quick security check of staged changes" \
  --timeout 120
```

### Batch Processing

```python
# process_files.py
import subprocess

files = ["mod1.py", "mod2.py", "mod3.py"]
for file in files:
    cmd = f'claude-mpm run --subprocess -i "Refactor {file} for performance"'
    subprocess.run(cmd, shell=True)
```

## Next Steps

- Master [Interactive Mode](interactive-mode.md) for conversations
- Learn about [Agent Delegation](../03-features/agent-delegation.md) in detail
- Explore [Session Logging](../03-features/session-logging.md) features
- See [CLI Reference](../04-reference/cli-commands.md) for all options