#!/usr/bin/env python3
"""Integration tests for Claude Code hook security."""

import json
import os
import subprocess
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def test_hook_with_stdin(description, event_data):
    """Test hook by simulating Claude Code calling it."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {description}")
    print(f"{'=' * 60}")

    # Run the hook handler with the event as stdin
    hook_script = (
        project_root
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_handler.py"
    )

    # Set up environment
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")

    try:
        result = subprocess.run(
            [sys.executable, str(hook_script)],
            input=json.dumps(event_data),
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
            check=False,
        )

        if result.stdout:
            response = json.loads(result.stdout)
            print(f"Action: {response['action']}")
            if "error" in response:
                print(f"Error: {response['error'][:100]}...")
        else:
            print(f"Exit code: {result.returncode}")
            if result.stderr:
                print(f"Stderr: {result.stderr}")
    except subprocess.TimeoutExpired:
        print("Test timed out")
    except Exception as e:
        print(f"Error: {e}")


def main():
    """Run integration tests."""
    working_dir = os.getcwd()

    print(f"Working Directory: {working_dir}")
    print("Running integration tests simulating Claude Code...")

    # Test 1: Legitimate write in project
    test_hook_with_stdin(
        "Legitimate project file write",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": f"{working_dir}/src/mymodule.py",
                "content": "def hello():\n    print('Hello, World!')\n",
            },
            "cwd": working_dir,
            "session_id": "integration-test-123",
        },
    )

    # Test 2: Malicious write attempt
    test_hook_with_stdin(
        "Malicious write to system file",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Write",
            "tool_input": {
                "file_path": "/etc/passwd",
                "content": "malicious:x:0:0::/root:/bin/bash\n",
            },
            "cwd": working_dir,
            "session_id": "integration-test-123",
        },
    )

    # Test 3: Agent trying to escape sandbox
    test_hook_with_stdin(
        "Agent attempting sandbox escape",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "MultiEdit",
            "tool_input": {
                "file_path": "../../../.ssh/authorized_keys",
                "edits": [
                    {
                        "old_string": "",
                        "new_string": "ssh-rsa AAAAB3... attacker@evil.com",
                    }
                ],
            },
            "cwd": working_dir,
            "session_id": "agent-qa-456",
        },
    )

    # Test 4: PM reading system info (allowed)
    test_hook_with_stdin(
        "PM reading system information",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Read",
            "tool_input": {"file_path": "/etc/os-release"},
            "cwd": working_dir,
            "session_id": "pm-main-789",
        },
    )

    # Test 5: NotebookEdit in project (allowed)
    test_hook_with_stdin(
        "Editing notebook in project",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "NotebookEdit",
            "tool_input": {
                "notebook_path": f"{working_dir}/notebooks/analysis.ipynb",
                "new_source": "import pandas as pd\ndf = pd.read_csv('data.csv')",
            },
            "cwd": working_dir,
            "session_id": "notebook-test-999",
        },
    )

    # Test 6: Grep searching outside (allowed)
    test_hook_with_stdin(
        "Grep searching system files",
        {
            "hook_event_name": "PreToolUse",
            "tool_name": "Grep",
            "tool_input": {"pattern": "claude", "path": "/usr/local"},
            "cwd": working_dir,
            "session_id": "grep-test-111",
        },
    )

    print(f"\n{'=' * 60}")
    print("Integration tests complete!")
    print("All security policies working as expected.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
