# Interactive Subprocess Orchestrator Usage Guide

## Overview

The Interactive Subprocess Orchestrator provides advanced control over Claude CLI sessions using `pexpect`, enabling:

- **Parallel subprocess execution** for agent delegations
- **Memory monitoring** with configurable thresholds
- **Interactive control** of Claude CLI processes
- **Resource management** with timeout and memory limits

## Installation

Add the required dependencies to your project:

```bash
pip install pexpect psutil
```

Or update your `requirements.txt`:
```
pexpect>=4.8.0
psutil>=5.9.0
```

## Command Line Usage

### Basic Usage

Use the `--interactive-subprocess` flag to enable interactive subprocess orchestration:

```bash
# Run with interactive subprocess orchestration
claude-mpm --interactive-subprocess -i "Create a Python web server with tests"

# With logging enabled
claude-mpm --interactive-subprocess --logging INFO -i "Implement a REST API"

# Disable parallel execution
claude-mpm --interactive-subprocess --no-parallel -i "Debug this code"
```

### Options

- `--interactive-subprocess`: Enable interactive subprocess orchestration
- `--logging [OFF|INFO|DEBUG]`: Set logging level (default: OFF)
- `--no-parallel`: Disable parallel execution of delegations
- `--no-tickets`: Disable automatic ticket creation
- `-i, --input`: Provide input prompt (required for orchestration mode)

## How It Works

### 1. Delegation Detection

The orchestrator detects delegation patterns in PM responses:

```
**Engineer Agent**: Create a factorial function
**QA**: Write comprehensive tests
Task Tool → Documentation Agent: Generate API docs
```

### 2. Subprocess Creation

Each detected delegation creates a controlled subprocess:

- Independent Claude CLI process
- Isolated environment with agent-specific context
- Memory monitoring with configurable limits
- Timeout protection

### 3. Parallel Execution

By default, delegations run in parallel:

```
PM Response:
  Detected 3 delegations. Running subprocesses...

[✓] Engineer: Create factorial function (2.3s, 156MB)
[✓] QA: Write comprehensive tests (3.1s, 198MB)
[✓] Documentation: Generate API docs (1.8s, 142MB)

Total execution time: 3.1s (parallel)
```

### 4. Memory Management

Each subprocess has memory monitoring:

- **Warning threshold**: 50% of limit
- **Critical threshold**: 80% of limit
- **Hard limit**: Process termination

Example configuration:
```python
result = orchestrator.run_agent_subprocess(
    agent="Engineer",
    task="Complex computation",
    memory_limit_mb=1024,  # 1GB limit
    timeout=300  # 5 minute timeout
)
```

## Example Session

### Input Prompt
```bash
claude-mpm --interactive-subprocess --logging INFO -i "Create a Python calculator with GUI, tests, and documentation"
```

### Expected Output
```
=== PM Response ===
I'll help you create a Python calculator with GUI, tests, and documentation. Let me coordinate the appropriate agents for this task.

**Engineer Agent**: Create a Python calculator with tkinter GUI supporting basic operations (+, -, *, /)

**QA Agent**: Write comprehensive unit tests for the calculator logic and integration tests for the GUI

**Documentation Agent**: Generate user documentation and API reference for the calculator

==================

Detected 3 delegations. Running subprocesses...

## Subprocess Execution Summary
- Total delegations: 3
- Successful: 3
- Failed: 0
- Total execution time: 4.2s

## Execution Details
1. [✓] Engineer: Create a Python calculator with tkinter GUI...
   - Execution time: 4.2s
   - Memory usage: 287MB
   - Exit code: 0

2. [✓] QA: Write comprehensive unit tests...
   - Execution time: 3.8s
   - Memory usage: 234MB
   - Exit code: 0

3. [✓] Documentation: Generate user documentation...
   - Execution time: 2.1s
   - Memory usage: 189MB
   - Exit code: 0

## Agent Responses

### Engineer Agent
--------------------------------------------------
I'll create a Python calculator with a tkinter GUI. Here's the implementation:

```python
# calculator.py
import tkinter as tk
from tkinter import ttk

class Calculator:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Python Calculator")
        # ... (implementation details)
```

### QA Agent
--------------------------------------------------
I'll write comprehensive tests for the calculator. Here are the test files:

```python
# test_calculator.py
import unittest
from calculator import Calculator
# ... (test implementation)
```

### Documentation Agent
--------------------------------------------------
I'll create documentation for the calculator application:

# Calculator User Guide
... (documentation content)
```

## Architecture

### ProcessManager

Manages subprocess lifecycles:

```python
class ProcessManager:
    def create_interactive_process(command, env, memory_limit_mb, timeout)
    def send_to_process(process_id, input_data)
    def read_from_process(process_id, pattern, timeout)
    def terminate_process(process_id)
    def get_active_processes()
```

### MemoryMonitor

Monitors process memory usage:

```python
class MemoryMonitor:
    def start_monitoring(process_pid)
    def stop_monitoring()
    def get_memory_usage(process_pid)
```

### InteractiveSubprocessOrchestrator

Main orchestration logic:

```python
class InteractiveSubprocessOrchestrator:
    def detect_delegations(response)
    def create_agent_prompt(agent, task, context)
    def run_agent_subprocess(agent, task, context, timeout, memory_limit_mb)
    def run_parallel_delegations(delegations)
    def run_orchestrated_session(initial_prompt)
```

## Advanced Configuration

### Custom Memory Limits

Set per-agent memory limits:

```python
orchestrator = InteractiveSubprocessOrchestrator()

# Configure specific agents
orchestrator.agent_memory_limits = {
    "Engineer": 2048,      # 2GB for code generation
    "QA": 1024,           # 1GB for testing
    "Documentation": 512   # 512MB for docs
}
```

### Parallel Execution Control

```python
# Limit parallel processes
orchestrator.max_parallel_processes = 4

# Disable parallel execution
orchestrator.parallel_execution_enabled = False
```

### Custom Timeouts

```python
# Global timeout
orchestrator.default_timeout = 600  # 10 minutes

# Per-agent timeouts
orchestrator.agent_timeouts = {
    "Engineer": 900,      # 15 minutes for complex tasks
    "QA": 600,           # 10 minutes for testing
    "Documentation": 300  # 5 minutes for docs
}
```

## Troubleshooting

### Common Issues

1. **pexpect not found**
   ```
   ModuleNotFoundError: No module named 'pexpect'
   ```
   Solution: Install with `pip install pexpect psutil`

2. **Claude CLI not found**
   ```
   FileNotFoundError: [Errno 2] No such file or directory: 'claude'
   ```
   Solution: Ensure Claude CLI is installed and in PATH

3. **Memory limit exceeded**
   ```
   Process 12345 exceeded hard limit (2048.0MB > 2048.0MB)
   ```
   Solution: Increase memory limit or optimize agent prompts

4. **Timeout errors**
   ```
   Timeout reading from process abc-123
   ```
   Solution: Increase timeout or check for hanging processes

### Debug Mode

Enable detailed logging:

```bash
claude-mpm --interactive-subprocess --logging DEBUG -i "task" --log-dir ./debug_logs
```

This creates detailed logs including:
- Process creation/termination
- Memory usage over time
- Input/output for each subprocess
- Delegation detection details

## Best Practices

1. **Use specific prompts** to ensure clear delegations
2. **Monitor resource usage** in production environments
3. **Set appropriate timeouts** based on task complexity
4. **Enable logging** for debugging complex workflows
5. **Test with --no-parallel** first to isolate issues

## Integration with Existing Code

The interactive subprocess orchestrator integrates seamlessly with the existing claude-mpm framework:

```python
from src.orchestration.interactive_subprocess_orchestrator import InteractiveSubprocessOrchestrator

# Create orchestrator
orchestrator = InteractiveSubprocessOrchestrator(
    framework_path="/path/to/framework",
    agents_dir="/path/to/agents",
    log_level="INFO"
)

# Run orchestrated session
orchestrator.run_orchestrated_session("Your prompt here")

# Get status
status = orchestrator.get_status()
print(f"Active processes: {len(status['active_processes'])}")
```

## Future Enhancements

Planned improvements include:

1. **Streaming output** - Real-time display of agent responses
2. **Progress indicators** - Visual feedback during execution
3. **Resource profiles** - Pre-configured resource limits by task type
4. **Caching** - Reuse results for identical delegations
5. **Web UI** - Browser-based monitoring and control