# PreToolUse Hook Input Modification

## Overview

Claude Code v2.0.30+ introduced the ability for PreToolUse hooks to modify tool inputs before execution. This powerful feature enables:

- **Context Injection**: Automatically add project context to file operations
- **Security Guards**: Validate and block potentially dangerous operations
- **Logging & Auditing**: Track all tool invocations before execution
- **Parameter Enhancement**: Add default parameters or normalize inputs

## Requirements

- Claude Code v2.0.30 or higher
- claude-mpm configured with hook support
- Hook scripts with `modifyInput: true` in configuration

## Version Detection

claude-mpm automatically detects Claude Code version and enables PreToolUse input modification features when supported:

```python
from claude_mpm.hooks.claude_hooks.installer import HookInstaller

installer = HookInstaller()

# Check if input modification is supported
if installer.supports_pretool_modify():
    print("PreToolUse input modification supported!")
else:
    version = installer.get_claude_version()
    print(f"Upgrade to Claude Code 2.0.30+ (current: {version})")
```

## Hook Configuration

### Basic Configuration

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/your/hook/script.py",
            "modifyInput": true
          }
        ]
      }
    ]
  }
}
```

### Tool-Specific Configuration

Target specific tools only:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/edit-guard.py",
            "modifyInput": true
          }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "/path/to/bash-timeout.py",
            "modifyInput": true
          }
        ]
      }
    ]
  }
}
```

## Hook Script Format

### Input Format (stdin)

Your hook receives JSON on stdin:

```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "foo",
    "new_string": "bar"
  },
  "session_id": "abc123...",
  "cwd": "/working/directory"
}
```

### Output Format (stdout)

Your hook must output JSON to stdout:

#### Continue with Modified Input

```json
{
  "action": "continue",
  "tool_input": {
    "file_path": "/path/to/file.py",
    "old_string": "foo",
    "new_string": "bar_modified"
  }
}
```

#### Continue Without Modification

```json
{
  "action": "continue"
}
```

#### Block Execution

```json
{
  "action": "block",
  "message": "Reason for blocking the operation"
}
```

## Example Implementations

### 1. Simple Parameter Enhancement

Add default parameters to tool calls:

```python
#!/usr/bin/env python3
import json
import sys

def main():
    event = json.loads(sys.stdin.read())
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Add line numbers to all Grep operations
    if tool_name == "Grep" and "-n" not in tool_input:
        modified = tool_input.copy()
        modified["-n"] = True
        print(json.dumps({"action": "continue", "tool_input": modified}))
        return

    # Default: continue without modification
    print(json.dumps({"action": "continue"}))

if __name__ == "__main__":
    main()
```

### 2. Security Guard

Block operations on sensitive files:

```python
#!/usr/bin/env python3
import json
import sys

BLOCKED_PATHS = [".env", "credentials.json", "secrets/", ".ssh/"]

def main():
    event = json.loads(sys.stdin.read())
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    if tool_name in ["Write", "Edit", "Read"]:
        file_path = tool_input.get("file_path", "")
        for blocked in BLOCKED_PATHS:
            if blocked in file_path:
                print(json.dumps({
                    "action": "block",
                    "message": f"Access to {file_path} blocked for security"
                }))
                return

    print(json.dumps({"action": "continue"}))

if __name__ == "__main__":
    main()
```

### 3. Context Injection

Add project context to file operations:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def load_project_context():
    """Load project context from .claude-context file."""
    context_file = Path.cwd() / ".claude-context"
    if context_file.exists():
        return context_file.read_text()
    return ""

def main():
    event = json.loads(sys.stdin.read())
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    if tool_name == "Read":
        context = load_project_context()
        if context:
            modified = tool_input.copy()
            # Add context as metadata (conceptual example)
            modified["_project_context"] = context[:200]
            print(json.dumps({"action": "continue", "tool_input": modified}))
            return

    print(json.dumps({"action": "continue"}))

if __name__ == "__main__":
    main()
```

### 4. Logging & Auditing

Log all tool invocations:

```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

def main():
    event = json.loads(sys.stdin.read())
    tool_name = event.get("tool_name", "")
    tool_input = event.get("tool_input", {})

    # Log the tool call
    log_file = Path.home() / ".claude-mpm" / "tool-calls.log"
    log_file.parent.mkdir(exist_ok=True)

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "session_id": event.get("session_id", "")[:16],
        "cwd": event.get("cwd", ""),
        "parameters": list(tool_input.keys())
    }

    with log_file.open("a") as f:
        f.write(json.dumps(log_entry) + "\n")

    # Continue without modification
    print(json.dumps({"action": "continue"}))

if __name__ == "__main__":
    main()
```

## Using Hook Templates

claude-mpm provides ready-to-use hook templates in `src/claude_mpm/hooks/templates/`:

### Full Template with Examples

```bash
# Copy the comprehensive template
cp src/claude_mpm/hooks/templates/pre_tool_use_template.py \
   ~/.claude-mpm/hooks/my_hook.py

# Make it executable
chmod +x ~/.claude-mpm/hooks/my_hook.py

# Edit and uncomment the example you want to use
nano ~/.claude-mpm/hooks/my_hook.py
```

The template includes:
- `ContextInjectionHook`: Auto-inject project context
- `SecurityGuardHook`: Validate file paths
- `LoggingHook`: Log all tool calls
- `ParameterEnhancementHook`: Add default parameters

### Simple Template

For basic use cases, use the simple template:

```bash
cp src/claude_mpm/hooks/templates/pre_tool_use_simple.py \
   ~/.claude-mpm/hooks/my_hook.py
```

## Best Practices

### 1. Always Handle Errors Gracefully

Never let your hook crash - always output a valid continue response:

```python
try:
    # Your hook logic
    modified = modify_input(event)
    print(json.dumps({"action": "continue", "tool_input": modified}))
except Exception as e:
    # Log error but don't block Claude
    print(f"Hook error: {e}", file=sys.stderr)
    print(json.dumps({"action": "continue"}))
```

### 2. Performance Matters

Hooks are executed synchronously and block Claude. Keep them fast:

```python
# ❌ Bad: Slow operation
def load_context():
    time.sleep(5)  # Too slow!
    return heavy_computation()

# ✅ Good: Fast operation
def load_context():
    # Use cached context
    return CACHED_CONTEXT
```

### 3. Use Debug Logging

Enable debug mode for development:

```python
import os
DEBUG = os.environ.get("CLAUDE_MPM_HOOK_DEBUG", "false").lower() == "true"

if DEBUG:
    print(f"Processing {tool_name}", file=sys.stderr)
```

Set the environment variable:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

### 4. Validate Modified Input

Ensure modified input is valid:

```python
def modify_input(tool_input):
    modified = tool_input.copy()

    # Validate modifications
    if "file_path" in modified:
        # Ensure it's still a valid path
        if not modified["file_path"].startswith("/"):
            return None  # Invalid, don't modify

    return modified
```

### 5. Document Your Hooks

Add clear comments explaining what your hook does:

```python
"""
Security Guard Hook for Claude MPM

This hook blocks operations on sensitive files including:
- .env files (environment variables)
- credentials.json (API keys)
- .ssh/ directory (SSH keys)

Requires: Claude Code 2.0.30+
"""
```

## Testing Your Hook

### Manual Testing

Test your hook with sample input:

```bash
echo '{
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {"file_path": "/test.py", "old_string": "a", "new_string": "b"},
  "session_id": "test123",
  "cwd": "/tmp"
}' | python3 your_hook.py
```

Expected output:
```json
{"action": "continue", "tool_input": {...}}
```

### Integration Testing

1. Configure your hook in settings.json
2. Enable debug mode: `export CLAUDE_MPM_HOOK_DEBUG=true`
3. Run Claude Code and watch stderr for hook output
4. Verify tool modifications take effect

### Automated Testing

Create test cases for your hook:

```python
import unittest
import json
from io import StringIO
import sys

class TestMyHook(unittest.TestCase):
    def test_grep_line_numbers(self):
        # Simulate stdin
        input_data = {
            "tool_name": "Grep",
            "tool_input": {"pattern": "foo"}
        }
        sys.stdin = StringIO(json.dumps(input_data))

        # Capture stdout
        sys.stdout = StringIO()

        # Run hook
        main()

        # Check output
        output = json.loads(sys.stdout.getvalue())
        self.assertEqual(output["action"], "continue")
        self.assertTrue("-n" in output["tool_input"])
```

## Troubleshooting

### Hook Not Being Called

1. Check Claude Code version: `claude --version`
2. Verify settings.json configuration
3. Ensure script is executable: `chmod +x your_hook.py`
4. Check hook script path is absolute

### Hook Errors

Enable debug logging:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
tail -f /tmp/claude-mpm-hook-error.log
```

### Input Not Being Modified

1. Verify `"modifyInput": true` is set in settings.json
2. Check hook outputs valid `tool_input` in response
3. Ensure Claude Code version is 2.0.30+

### Performance Issues

If hooks are slow:
1. Add timing logs to identify bottlenecks
2. Cache expensive operations
3. Consider async processing for non-blocking operations

## Advanced Use Cases

### Chaining Multiple Hooks

Configure multiple hooks in sequence:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {"type": "command", "command": "/path/to/logger.py", "modifyInput": true},
          {"type": "command", "command": "/path/to/guard.py", "modifyInput": true},
          {"type": "command", "command": "/path/to/enhancer.py", "modifyInput": true}
        ]
      }
    ]
  }
}
```

Each hook receives the output of the previous hook.

### Conditional Modification

Modify input based on context:

```python
def modify_input(event):
    tool_name = event["tool_name"]
    tool_input = event["tool_input"]
    session_id = event.get("session_id", "")
    cwd = event.get("cwd", "")

    # Different behavior based on working directory
    if "/sensitive/project" in cwd:
        # Extra security for sensitive projects
        if tool_name == "Bash":
            return None  # Block all bash commands

    return tool_input
```

### Integration with External Services

Call external APIs for validation:

```python
import requests

def validate_with_api(file_path):
    """Check if file operation is allowed via external API."""
    response = requests.get(
        "https://api.example.com/validate",
        params={"path": file_path},
        timeout=0.5  # Keep it fast!
    )
    return response.json()["allowed"]

def main():
    event = json.loads(sys.stdin.read())
    # ... validation logic
```

## Reference

### Supported Tools

PreToolUse hooks work with all Claude Code tools:

- **File Operations**: Read, Write, Edit, MultiEdit
- **File System**: LS, Glob, Find
- **Execution**: Bash, NotebookEdit
- **Delegation**: Task
- **Search**: Grep

### Hook Lifecycle

1. Claude decides to use a tool
2. PreToolUse hook is triggered
3. Hook receives event on stdin
4. Hook processes and outputs response
5. Claude receives modified input (or block)
6. Tool executes with modified input
7. PostToolUse hook triggered after execution

### Environment Variables

- `CLAUDE_MPM_HOOK_DEBUG`: Enable debug logging
- `CLAUDE_MPM_SOCKETIO_PORT`: Socket.IO port for event emission

## Migration Guide

### From Legacy Hooks

If you have existing PreToolUse hooks without input modification:

**Before (Legacy):**
```python
def main():
    event = json.loads(sys.stdin.read())
    # Just emit events, can't modify
    emit_event(event)
    print(json.dumps({"action": "continue"}))
```

**After (v2.0.30+):**
```python
def main():
    event = json.loads(sys.stdin.read())
    # Can now modify input
    modified = enhance_input(event)
    print(json.dumps({"action": "continue", "tool_input": modified}))
```

### Backward Compatibility

Your hooks remain compatible:
- Hooks without `modifyInput: true` continue to work
- Hooks can output `{"action": "continue"}` without modifications
- Graceful degradation on older Claude Code versions

## See Also

- [Hook Templates](../../src/claude_mpm/hooks/templates/)
- [Claude Code Hook API](https://docs.anthropic.com/claude-code/hooks)
