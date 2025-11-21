#!/usr/bin/env python3
"""Test script to verify the hook duplicate fix."""

import json
import subprocess
import sys
import time
from pathlib import Path


def test_hook_handler():
    """Test that the hook handler only outputs one continue message."""

    # Create a test event
    test_event = {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session-123",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test"},
        "cwd": "/tmp",
    }

    event_json = json.dumps(test_event)

    # Path to hook handler
    (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_handler.py"
    )

    print("Testing hook handler duplicate detection...")
    print(f"Event: {test_event['hook_event_name']}")
    print("-" * 50)

    # Run the hook handler multiple times in quick succession
    # to simulate Claude Code calling it multiple times
    outputs = []
    for i in range(3):
        print(f"\nInvocation {i + 1}:")
        result = subprocess.run(
            [sys.executable, "-m", "claude_mpm.hooks.claude_hooks.hook_handler"],
            input=event_json,
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            env={
                **subprocess.os.environ,
                "PYTHONPATH": str(Path(__file__).parent.parent / "src"),
            },
            check=False,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        if stdout:
            outputs.append(stdout)
            print(f"  stdout: {stdout}")
        if stderr:
            print("  stderr output (debug):")
            for line in stderr.split("\n"):
                if line:
                    print(f"    {line}")

        # Small delay between invocations
        time.sleep(0.01)

    print("\n" + "=" * 50)
    print("RESULTS:")
    print("Total invocations: 3")
    print(f"Total outputs: {len(outputs)}")
    print(f"Outputs: {outputs}")

    # Check that all invocations output continue
    # (each invocation needs to output continue to not block Claude)
    expected_output = '{"action": "continue"}'
    all_correct = all(output == expected_output for output in outputs)

    if len(outputs) == 3 and all_correct:
        print("\n✅ SUCCESS: Each invocation correctly output a single continue")
        print("   The hook handler properly handles multiple invocations")
        return True
    print(f"\n❌ FAILURE: Expected 3 continues, got {len(outputs)}")
    return False


if __name__ == "__main__":
    success = test_hook_handler()
    sys.exit(0 if success else 1)
