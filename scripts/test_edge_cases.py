#!/usr/bin/env python3
"""Test edge cases for hook security."""

import json
import sys
import os
import tempfile
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
            print(f"Error Message: {response['error'][:100]}...")
    else:
        print("No output (would continue normally)")


def main():
    """Run edge case tests."""
    working_dir = os.getcwd()
    
    print(f"Working Directory: {working_dir}")
    
    # Test 1: Empty file path
    test_scenario(
        "Empty file path",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "",
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 2: Null byte injection
    test_scenario(
        "Null byte injection attempt",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": f"{working_dir}/test.txt\x00/etc/passwd",
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 3: Unicode directory traversal
    test_scenario(
        "Unicode directory traversal",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {
                "file_path": f"{working_dir}/\u002e\u002e/\u002e\u002e/etc/passwd",
                "old_string": "test",
                "new_string": "hacked"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 4: Write to temp directory (blocked)
    temp_file = tempfile.mktemp()
    test_scenario(
        "Write to temp directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": temp_file,
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 5: Special characters in path
    test_scenario(
        "Special characters in path",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": f"{working_dir}/test$file@name#.txt",
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 6: Very long path
    long_path = f"{working_dir}/" + "a" * 1000 + ".txt"
    test_scenario(
        "Very long path",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": long_path,
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 7: Missing file_path key
    test_scenario(
        "Missing file_path key",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 8: Non-string file_path
    test_scenario(
        "Non-string file_path",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": 12345,
                "content": "test"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 9: Grep tool (should be allowed anywhere)
    test_scenario(
        "Grep outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": {
                "pattern": "password",
                "path": "/etc"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    # Test 10: LS tool (should be allowed anywhere)
    test_scenario(
        "LS outside working directory",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "LS",
            "tool_input": {
                "path": "/etc"
            },
            "cwd": working_dir,
            "session_id": "test-123"
        }
    )
    
    print(f"\n{'='*60}")
    print("Edge case tests complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()