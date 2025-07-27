#!/usr/bin/env python3
"""Manual test script to demonstrate hook security features."""

import json
import sys
import os
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / 'src'))

from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler


def test_scenario(description, event):
    """Test a specific scenario."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{'='*60}")
    
    handler = ClaudeHookHandler()
    handler.event = event
    handler.hook_type = event['hook_event_name']
    
    # Capture the response
    import io
    from contextlib import redirect_stdout
    
    output = io.StringIO()
    try:
        with redirect_stdout(output):
            handler._handle_pre_tool_use()
    except SystemExit:
        pass
    
    result = output.getvalue()
    if result:
        response = json.loads(result)
        print(f"Action: {response['action']}")
        if 'error' in response:
            print(f"Error: {response['error']}")
    else:
        print("No output (would continue normally)")


def main():
    """Run security tests."""
    working_dir = os.getcwd()
    
    print(f"Working Directory: {working_dir}")
    
    # Test 1: Write within working directory (allowed)
    test_scenario(
        "Write within working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": f"{working_dir}/test.txt",
                "content": "This is allowed"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 2: Write outside working directory (blocked)
    test_scenario(
        "Write outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/etc/passwd",
                "content": "This should be blocked"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 3: Path traversal attempt (blocked)
    test_scenario(
        "Path traversal attempt",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": f"{working_dir}/../../../etc/passwd",
                "old_string": "root",
                "new_string": "hacked"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 4: Read from anywhere (allowed)
    test_scenario(
        "Read from outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {
                "file_path": "/etc/hosts"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 5: MultiEdit outside directory (blocked)
    test_scenario(
        "MultiEdit outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": "/tmp/dangerous.txt",
                "edits": [
                    {"old_string": "safe", "new_string": "dangerous"}
                ]
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 6: NotebookEdit outside directory (blocked)
    test_scenario(
        "NotebookEdit outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "NotebookEdit",
            "tool_input": {
                "notebook_path": "/home/user/notebook.ipynb",
                "new_source": "malicious code"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    print(f"\n{'='*60}")
    print("Security tests complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()