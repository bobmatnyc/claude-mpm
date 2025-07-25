# Claude Launcher Migration Guide

This guide shows how to migrate orchestrators to use the unified `ClaudeLauncher` class.

## Overview

The `ClaudeLauncher` class provides a single endpoint for all Claude CLI launches, replacing the redundant command building and subprocess handling across orchestrators.

## Before (Old Pattern)

```python
# Building command manually
cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions", "--print"]

# Running subprocess
result = subprocess.run(
    cmd,
    input=prompt,
    capture_output=True,
    text=True,
    timeout=60
)

if result.returncode == 0:
    response = result.stdout.strip()
else:
    error = result.stderr
```

## After (Using ClaudeLauncher)

```python
from claude_mpm.core import ClaudeLauncher, LaunchMode

# Initialize launcher once
launcher = ClaudeLauncher(model="opus", skip_permissions=True)

# One-shot execution
stdout, stderr, returncode = launcher.launch_oneshot(
    message=prompt,
    use_stdin=True,
    timeout=60
)

if returncode == 0:
    response = stdout.strip()
else:
    error = stderr
```

## Migration Examples

### 1. Interactive Mode

**Before:**
```python
cmd = ["claude", "--dangerously-skip-permissions"]
process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
```

**After:**
```python
process = launcher.launch_interactive()
# or with more control:
process = launcher.launch(mode=LaunchMode.INTERACTIVE)
```

### 2. Print Mode with Direct Args

**Before:**
```python
cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions", "--print", message]
result = subprocess.run(cmd, capture_output=True, text=True)
```

**After:**
```python
stdout, stderr, returncode = launcher.launch_oneshot(
    message=message,
    use_stdin=False  # Pass as command arg instead of stdin
)
```

### 3. System Prompt Mode

**Before:**
```python
cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions", 
       "--append-system-prompt", framework_content]
process = subprocess.run(cmd, capture_output=True, text=True)
```

**After:**
```python
process = launcher.launch_with_system_prompt(
    system_prompt=framework_content
)
# Wait for completion
stdout, stderr = process.communicate()
```

### 4. Custom Popen Arguments

**Before:**
```python
process = subprocess.Popen(
    ["claude", "--model", "opus", "--dangerously-skip-permissions"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    env=custom_env,
    cwd=working_dir,
    preexec_fn=os.setsid
)
```

**After:**
```python
process = launcher.launch(
    mode=LaunchMode.INTERACTIVE,
    env=custom_env,
    cwd=working_dir,
    preexec_fn=os.setsid
)
```

### 5. PTY Mode

For PTY mode, you can still use the launcher with custom file descriptors:

```python
import pty

# Create PTY
master, slave = pty.openpty()

# Launch with PTY
process = launcher.launch(
    mode=LaunchMode.INTERACTIVE,
    stdin=slave,
    stdout=slave,
    stderr=slave
)
```

## Benefits

1. **Single source of truth** for Claude command construction
2. **Consistent error handling** across all orchestrators
3. **Automatic Claude path discovery** with fallback locations
4. **Type-safe launch modes** using the `LaunchMode` enum
5. **Simplified subprocess management** with built-in timeout handling
6. **Future-proof** - changes to Claude CLI flags only need updates in one place

## Complete Example: Migrating an Orchestrator

Here's a complete example from the `SubprocessOrchestrator`:

```python
class SubprocessOrchestrator:
    def __init__(self, ...):
        # Initialize launcher once
        self.launcher = ClaudeLauncher(
            model="opus",
            skip_permissions=True,
            log_level=log_level
        )
    
    def run_delegation(self, agent, task):
        # Use launcher for delegations
        stdout, stderr, returncode = self.launcher.launch_oneshot(
            message=build_prompt(agent, task),
            timeout=60
        )
        
        if returncode == 0:
            return stdout.strip()
        else:
            raise RuntimeError(f"Delegation failed: {stderr}")
    
    def run_interactive(self):
        # Use launcher for interactive mode
        process = self.launcher.launch_interactive()
        process.wait()
```

## Testing

The unified launcher makes testing easier:

```python
# Mock the launcher for testing
mock_launcher = Mock(spec=ClaudeLauncher)
mock_launcher.launch_oneshot.return_value = ("response", "", 0)

# Test orchestrator behavior without actually launching Claude
orchestrator = MyOrchestrator(launcher=mock_launcher)
result = orchestrator.run_task("test")
assert result == "response"
```