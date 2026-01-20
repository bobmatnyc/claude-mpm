# Claude MPM Hook Templates

This directory contains ready-to-use hook templates for extending Claude Code functionality.

## Available Templates

### PreToolUse Hooks (Claude Code v2.0.30+)

#### `pre_tool_use_template.py`

Comprehensive template with multiple example implementations:

- **ContextInjectionHook**: Auto-inject project context into file operations
- **SecurityGuardHook**: Block operations on sensitive files
- **LoggingHook**: Log all tool invocations for debugging
- **ParameterEnhancementHook**: Add default parameters to tool calls

**Usage:**
```bash
# Copy and customize
cp pre_tool_use_template.py ~/.claude-mpm/hooks/my_hook.py
chmod +x ~/.claude-mpm/hooks/my_hook.py

# Edit to uncomment the implementation you want
nano ~/.claude-mpm/hooks/my_hook.py
```

#### `pre_tool_use_simple.py`

Minimal example for quick customization:

- Shows basic hook structure
- Includes simple parameter enhancement example
- Includes security guard example
- Easy to understand and modify

**Usage:**
```bash
# Copy for quick start
cp pre_tool_use_simple.py ~/.claude-mpm/hooks/my_hook.py
chmod +x ~/.claude-mpm/hooks/my_hook.py
```

## Configuration

Add hooks to `~/.claude/settings.json`:

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

## Requirements

- Claude Code v2.0.30+ for PreToolUse input modification
- Python 3.7+
- claude-mpm installed and configured

## Version Check

Check if your Claude Code version supports input modification:

```bash
claude --version
```

Or programmatically:

```python
from claude_mpm.hooks.claude_hooks.installer import HookInstaller

installer = HookInstaller()
if installer.supports_pretool_modify():
    print("✓ PreToolUse input modification supported")
else:
    print(f"✗ Requires Claude Code 2.0.30+ (current: {installer.get_claude_version()})")
```

## Documentation

See [PreToolUse Hook Documentation](../../../docs/developer/pretool-use-hooks.md) for:
- Detailed usage guide
- Best practices
- Testing strategies
- Troubleshooting
- Advanced examples

## Quick Examples

### Add Line Numbers to Grep

```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
if event.get("tool_name") == "Grep":
    modified = event["tool_input"].copy()
    modified["-n"] = True
    print(json.dumps({"continue": True, "tool_input": modified}))
else:
    print(json.dumps({"continue": True}))
```

### Block Sensitive Files

```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
tool_name = event.get("tool_name", "")
if tool_name in ["Write", "Edit", "Read"]:
    file_path = event["tool_input"].get("file_path", "")
    if ".env" in file_path:
        print(json.dumps({"continue": False, "stopReason": "Access to .env blocked"}))
        sys.exit(0)

print(json.dumps({"continue": True}))
```

### Add Default Timeout to Bash

```python
#!/usr/bin/env python3
import json
import sys

event = json.loads(sys.stdin.read())
if event.get("tool_name") == "Bash":
    modified = event["tool_input"].copy()
    if "timeout" not in modified:
        modified["timeout"] = 30000  # 30 seconds
        print(json.dumps({"continue": True, "tool_input": modified}))
        sys.exit(0)

print(json.dumps({"continue": True}))
```

## Testing Your Hook

Test manually with sample input:

```bash
echo '{
  "hook_event_name": "PreToolUse",
  "tool_name": "Grep",
  "tool_input": {"pattern": "test"},
  "session_id": "test123",
  "cwd": "/tmp"
}' | python3 your_hook.py
```

Enable debug mode:
```bash
export CLAUDE_MPM_HOOK_DEBUG=true
```

## Support

For issues or questions:
- See [Documentation](../../../docs/developer/pretool-use-hooks.md)
- Check [GitHub Issues](https://github.com/yourusername/claude-mpm/issues)
- Review [Examples](./pre_tool_use_template.py)
