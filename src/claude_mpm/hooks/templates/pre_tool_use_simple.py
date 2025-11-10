#!/usr/bin/env python3
"""
Simple PreToolUse Hook Example for Claude Code v2.0.30+

This is a minimal example showing the basic structure of a PreToolUse hook
that can modify tool inputs.

To use this hook:
1. Copy this file to ~/.claude-mpm/hooks/
2. Make it executable: chmod +x ~/.claude-mpm/hooks/pre_tool_use_simple.py
3. Add to ~/.claude/settings.json:

{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "/Users/YOUR_USERNAME/.claude-mpm/hooks/pre_tool_use_simple.py",
            "modifyInput": true
          }
        ]
      }
    ]
  }
}
"""

import json
import sys


def main():
    """Process PreToolUse event and optionally modify input."""
    try:
        # Read event from stdin
        event_data = sys.stdin.read()
        if not event_data.strip():
            print(json.dumps({"action": "continue"}))
            return

        event = json.loads(event_data)
        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        # Example: Add line numbers to all Grep operations
        if tool_name == "Grep" and "-n" not in tool_input:
            modified_input = tool_input.copy()
            modified_input["-n"] = True
            print(json.dumps({"action": "continue", "tool_input": modified_input}))
            return

        # Example: Block operations on .env files
        if tool_name in ["Write", "Edit", "Read"]:
            file_path = tool_input.get("file_path", "")
            if ".env" in file_path:
                print(
                    json.dumps(
                        {
                            "action": "block",
                            "message": "Access to .env file blocked for security",
                        }
                    )
                )
                return

        # Default: continue without modification
        print(json.dumps({"action": "continue"}))

    except Exception:
        # Always continue on error to avoid blocking Claude
        print(json.dumps({"action": "continue"}))


if __name__ == "__main__":
    main()
