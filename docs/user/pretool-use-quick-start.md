# PreToolUse Hooks Quick Start Guide

## What Are PreToolUse Hooks?

PreToolUse hooks let you modify tool inputs before Claude Code executes them. Think of them as "smart filters" that can:

- 🛡️ **Block dangerous operations** (e.g., prevent editing .env files)
- 📝 **Add default parameters** (e.g., always add line numbers to grep)
- 🔍 **Log tool usage** (e.g., track all file operations)
- 🎯 **Inject context** (e.g., add project info to file reads)

## Requirements

- Claude Code v2.0.30 or higher
- claude-mpm installed and configured

## Quick Version Check

```bash
claude --version
# Should show 2.0.30 or higher

# Or check programmatically
python3 -c "
from claude_mpm.hooks.claude_hooks.installer import HookInstaller
installer = HookInstaller()
if installer.supports_pretool_modify():
    print('✓ Ready to use PreToolUse hooks!')
else:
    print(f'✗ Need Claude Code 2.0.30+ (current: {installer.get_claude_version()})')
"
```

## 5-Minute Setup

### Step 1: Copy a Template

Choose based on your needs:

**Simple use case:**
```bash
cp src/claude_mpm/hooks/templates/pre_tool_use_simple.py \
   ~/.claude-mpm/hooks/my_hook.py
```

**Advanced use case:**
```bash
cp src/claude_mpm/hooks/templates/pre_tool_use_template.py \
   ~/.claude-mpm/hooks/my_hook.py
```

### Step 2: Make It Executable

```bash
chmod +x ~/.claude-mpm/hooks/my_hook.py
```

### Step 3: Configure Claude

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
            "command": "/Users/YOUR_USERNAME/.claude-mpm/hooks/my_hook.py",
            "modifyInput": true
          }
        ]
      }
    ]
  }
}
```

**Important:** Replace `YOUR_USERNAME` with your actual username!

### Step 4: Test It

```bash
# Test with sample input
echo '{
  "hook_event_name": "PreToolUse",
  "tool_name": "Grep",
  "tool_input": {"pattern": "test"},
  "session_id": "test123",
  "cwd": "/tmp"
}' | python3 ~/.claude-mpm/hooks/my_hook.py
```

You should see output like:
```json
{"action": "continue", "tool_input": {"pattern": "test", "-n": true}}
```

## Common Use Cases

### 1. Always Add Line Numbers to Grep

**Edit your hook:**
```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name", "")
tool_input = event.get("tool_input", {})

if tool_name == "Grep" and "-n" not in tool_input:
    modified = tool_input.copy()
    modified["-n"] = True
    print(json.dumps({"action": "continue", "tool_input": modified}))
else:
    print(json.dumps({"action": "continue"}))
```

**Result:** Every time Claude uses Grep, line numbers are automatically included!

### 2. Block Access to Sensitive Files

**Edit your hook:**
```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name", "")
tool_input = event.get("tool_input", {})

if tool_name in ["Write", "Edit", "Read"]:
    file_path = tool_input.get("file_path", "")
    if ".env" in file_path or "credentials" in file_path:
        print(json.dumps({
            "action": "block",
            "message": "Access to sensitive files blocked for security"
        }))
        sys.exit(0)

print(json.dumps({"action": "continue"}))
```

**Result:** Claude cannot edit or read .env or credentials files!

### 3. Add Default Timeout to Bash Commands

**Edit your hook:**
```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name", "")
tool_input = event.get("tool_input", {})

if tool_name == "Bash" and "timeout" not in tool_input:
    modified = tool_input.copy()
    modified["timeout"] = 30000  # 30 seconds
    print(json.dumps({"action": "continue", "tool_input": modified}))
else:
    print(json.dumps({"action": "continue"}))
```

**Result:** All Bash commands automatically get a 30-second timeout!

### 4. Log All Tool Usage

**Edit your hook:**
```python
#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name", "")
tool_input = event.get("tool_input", {})

# Log to file
log_file = Path.home() / ".claude-mpm" / "tool-usage.log"
log_file.parent.mkdir(exist_ok=True)

log_entry = {
    "timestamp": datetime.now().isoformat(),
    "tool": tool_name,
    "session": event.get("session_id", "")[:8],
    "params": list(tool_input.keys())
}

with log_file.open("a") as f:
    f.write(json.dumps(log_entry) + "\n")

print(json.dumps({"action": "continue"}))
```

**Result:** All tool usage logged to `~/.claude-mpm/tool-usage.log`!

## Debugging

### Enable Debug Mode

```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

Then run Claude Code from that terminal. Debug output goes to stderr.

### Check Hook Output

```bash
# Test your hook manually
echo '{
  "hook_event_name": "PreToolUse",
  "tool_name": "Edit",
  "tool_input": {"file_path": "/test.py", "old_string": "a", "new_string": "b"}
}' | python3 ~/.claude-mpm/hooks/my_hook.py
```

### Common Issues

**Hook not running:**
- Check Claude Code version: `claude --version`
- Verify settings.json path is absolute
- Ensure script is executable: `chmod +x your_hook.py`

**Hook errors:**
- Enable debug mode
- Test manually with sample input
- Check for Python syntax errors: `python3 -m py_compile your_hook.py`

**Not modifying input:**
- Verify `"modifyInput": true` in settings.json
- Check hook outputs `tool_input` in response
- Ensure Claude Code is 2.0.30+

## Tool-Specific Hooks

Target specific tools instead of all tools:

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

## Hook Response Format

Your hook must output JSON:

**Continue without changes:**
```json
{"action": "continue"}
```

**Continue with modified input:**
```json
{
  "action": "continue",
  "tool_input": {
    "file_path": "/test.py",
    "new_param": "value"
  }
}
```

**Block execution:**
```json
{
  "action": "block",
  "message": "Operation blocked: reason here"
}
```

## Available Tools

You can hook into these tools:

- **File Operations**: Read, Write, Edit, MultiEdit
- **File System**: LS, Glob, Find
- **Execution**: Bash, NotebookEdit
- **Delegation**: Task
- **Search**: Grep

## Next Steps

- 📖 Read the [full documentation](../developer/pretool-use-hooks.md)
- 🔍 Explore the [template examples](../../src/claude_mpm/hooks/templates/)
- 💡 Share your hooks with the community
- 🚀 Build advanced automation workflows

## Getting Help

- Check [troubleshooting guide](../developer/pretool-use-hooks.md#troubleshooting)
- Review [example implementations](../developer/pretool-use-hooks.md#example-implementations)
- Enable debug mode for detailed output
- Test hooks manually with sample input

## Tips for Success

1. **Start Simple**: Begin with the simple template
2. **Test First**: Always test with sample input before using
3. **Handle Errors**: Wrap logic in try/except to avoid blocking Claude
4. **Keep It Fast**: Hooks run synchronously - avoid slow operations
5. **Log for Debug**: Add debug output to stderr for troubleshooting
6. **Document Your Logic**: Add comments explaining what your hook does

---

**Ready to automate?** Copy a template and start customizing! 🚀
