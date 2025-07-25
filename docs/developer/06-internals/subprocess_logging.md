# Subprocess Utilities - Comprehensive Logging Guide

This document describes the comprehensive logging capabilities added to the subprocess utilities in claude-mpm.

## Overview

The subprocess utilities now include extensive logging at multiple levels:
- **DEBUG**: Detailed diagnostic information
- **INFO**: General process lifecycle events
- **WARNING**: Timeout and stderr output
- **ERROR**: Failures and exceptions

## Components

### 1. SubprocessRunner (Enhanced Base)

The base `SubprocessRunner` in `utils/subprocess_runner.py` now includes:
- Process counting with unique IDs (PROC-1, PROC-2, etc.)
- Execution time tracking
- Command detail logging
- Environment variable logging (with sensitive value masking)
- Output capture logging

### 2. EnhancedSubprocessRunner

Located in `utils/enhanced_subprocess_runner.py`, provides:
- Extended logging for all subprocess operations
- Process execution statistics tracking
- Detailed result logging with output truncation
- Success/failure counting

### 3. ProcessManager

Located in `utils/process.py`, provides:
- Process lifecycle tracking
- Resource usage monitoring (via psutil)
- Process spawning with comprehensive logging
- Graceful termination with logging

### 4. OutputFormatter

Located in `utils/output.py`, provides:
- Terminal width detection logging
- Output formatting operation logging
- Progress bar update tracking
- Table formatting with dimension logging

### 5. TerminalManager

Located in `utils/terminal.py`, provides:
- Terminal capability detection logging
- Terminal size detection with fallback methods
- Cursor control operation logging
- Raw mode and key reading support

## Logging Features

### Sensitive Data Protection

Environment variables with sensitive names are automatically masked:
- Keys containing: 'key', 'token', 'password', 'secret', 'auth'
- Logged as: `KEY_NAME: [MASKED]`

### Process Identification

Each subprocess gets a unique ID for tracking:
```
[PROC-1] Starting subprocess: echo Hello
[PROC-1] Subprocess completed: returncode=0, execution_time=0.015s
```

### Output Logging

- Stdout/stderr logged with character and line counts
- Automatic truncation for outputs > 500 characters
- Different log levels based on context (stderr uses WARNING if process failed)

### Execution Statistics

The EnhancedSubprocessRunner tracks:
- Total processes executed
- Success/failure counts
- Total and average execution times

## Usage Examples

### Basic Usage

```python
from claude_mpm.utils.subprocess_runner import SubprocessRunner

# Basic runner with default logging
runner = SubprocessRunner()
result = runner.run(['echo', 'Hello'])
```

### Enhanced Usage

```python
from claude_mpm.utils.enhanced_subprocess_runner import EnhancedSubprocessRunner

# Enhanced runner with comprehensive logging
runner = EnhancedSubprocessRunner()
result = runner.run(['python', 'script.py'])

# Get execution statistics
stats = runner.get_statistics()
print(f"Total processes: {stats['total_processes']}")
```

### Process Management

```python
from claude_mpm.utils.process import ProcessManager

manager = ProcessManager()

# Spawn process with logging
result = manager.spawn_process(
    ['python', 'long_running.py'],
    env={'API_KEY': 'secret'},  # Will be masked in logs
    timeout=30
)

# Track running process
manager.track_process(pid, command, start_time)
```

### Output Formatting

```python
from claude_mpm.utils.output import OutputFormatter

formatter = OutputFormatter()

# Create progress bar with logging
bar = formatter.create_progress_bar('download', total=100)
for i in range(100):
    formatter.update_progress_bar('download', i+1)
```

### Terminal Operations

```python
from claude_mpm.utils.terminal import TerminalManager

manager = TerminalManager()

# Detect capabilities with logging
caps = manager.detect_capabilities()

# Get terminal size with fallback logging
width, height = manager.get_terminal_size()
```

## Log Output Examples

### Successful Command
```
2025-07-25 10:30:15 - INFO - [PROC-1] Starting subprocess: git status
2025-07-25 10:30:15 - DEBUG - [PROC-1] Command details:
2025-07-25 10:30:15 - DEBUG -   Full command: ['git', 'status']
2025-07-25 10:30:15 - DEBUG -   Working directory: /Users/masa/Projects/claude-mpm
2025-07-25 10:30:15 - DEBUG -   Capture output: True
2025-07-25 10:30:15 - INFO - [PROC-1] Subprocess completed: returncode=0, execution_time=0.045s
2025-07-25 10:30:15 - DEBUG - [PROC-1] Stdout: 156 characters
```

### Failed Command with Timeout
```
2025-07-25 10:31:20 - INFO - [PROC-2] Starting subprocess with timeout 5s: sleep 10
2025-07-25 10:31:25 - WARNING - [PROC-2] Subprocess timed out after 5.003s (timeout was 5s)
```

### Environment Variable Masking
```
2025-07-25 10:32:00 - DEBUG - [PROC-3] Custom environment variables: 3 entries
2025-07-25 10:32:00 - DEBUG -     API_KEY: [MASKED]
2025-07-25 10:32:00 - DEBUG -     DEBUG: true
2025-07-25 10:32:00 - DEBUG -     PATH: /usr/local/bin:/usr/bin
```

## Configuration

### Custom Logger

```python
import logging

# Create custom logger
logger = logging.getLogger('my_app.subprocess')
logger.setLevel(logging.DEBUG)

# Use with subprocess utilities
runner = SubprocessRunner(logger=logger)
manager = ProcessManager(base_logger=logger)
```

### Log Level Control

```python
# Suppress verbose output
logger.setLevel(logging.INFO)  # Skip DEBUG messages

# Error-only mode
logger.setLevel(logging.ERROR)  # Only log errors
```

## Testing

Run the comprehensive test suite:

```bash
python tests/test_subprocess_logging.py
```

This will:
1. Test all subprocess utilities
2. Generate detailed logs in `/tmp/subprocess_logging_test.log`
3. Demonstrate all logging features

## Best Practices

1. **Use Process IDs**: The PROC-X IDs help track operations across log entries
2. **Check Statistics**: Use `get_statistics()` to monitor subprocess performance
3. **Handle Sensitive Data**: Be aware of automatic masking for security
4. **Monitor Timeouts**: Timeout events are logged as warnings for visibility
5. **Review Stderr**: Non-zero exit codes elevate stderr to WARNING level

## Future Enhancements

Potential improvements:
- Configurable output truncation limits
- Process group tracking
- Memory usage logging
- Custom log formatters for different use cases
- Integration with system monitoring tools