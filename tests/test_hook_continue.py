#!/usr/bin/env python3
"""Test script to verify that hook handler only outputs one continue message."""

import json
import subprocess
import sys
from pathlib import Path


def test_hook_handler():
    """Test that hook handler outputs exactly one continue message."""

    # Create a test event
    test_event = {
        "hook_event_name": "UserPromptSubmit",
        "session_id": "test-session-123",
        "prompt": "Test prompt",
    }

    # Path to hook handler
    hook_handler_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_handler.py"
    )

    if not hook_handler_path.exists():
        print(f"❌ Hook handler not found at {hook_handler_path}")
        return False

    # Run the hook handler as a module with proper PYTHONPATH
    import os

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).parent.parent / "src")

    result = subprocess.run(
        [sys.executable, "-m", "claude_mpm.hooks.claude_hooks.hook_handler"],
        input=json.dumps(test_event),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    # Check output
    output_lines = result.stdout.strip().split("\n")
    continue_lines = [line for line in output_lines if '{"action": "continue"}' in line]

    print(f"Test Event: {test_event['hook_event_name']}")
    print(f"Exit Code: {result.returncode}")
    print(f"Output Lines: {len(output_lines)}")
    print(f"Continue Lines Found: {len(continue_lines)}")

    if len(continue_lines) == 1:
        print("✅ PASS: Exactly one continue message")
        return True
    print(f"❌ FAIL: Expected 1 continue message, got {len(continue_lines)}")
    print("Output:")
    for i, line in enumerate(output_lines, 1):
        print(f"  {i}: {line}")
    return False


def test_hook_wrapper():
    """Test that hook wrapper + handler outputs exactly one continue message."""

    # Create a test event
    test_event = {
        "hook_event_name": "PreToolUse",
        "session_id": "test-session-456",
        "tool_name": "Bash",
        "arguments": {"command": "echo test"},
    }

    # Path to hook wrapper
    hook_wrapper_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "hooks"
        / "claude_hooks"
        / "hook_wrapper.sh"
    )

    if not hook_wrapper_path.exists():
        print(f"❌ Hook wrapper not found at {hook_wrapper_path}")
        return False

    # Run the hook wrapper with the test event
    result = subprocess.run(
        ["bash", str(hook_wrapper_path)],
        input=json.dumps(test_event),
        capture_output=True,
        text=True,
        check=False,
    )

    # Check output
    output_lines = result.stdout.strip().split("\n")
    continue_lines = [line for line in output_lines if '{"action": "continue"}' in line]

    print(f"\nTest Event: {test_event['hook_event_name']}")
    print(f"Exit Code: {result.returncode}")
    print(f"Output Lines: {len(output_lines)}")
    print(f"Continue Lines Found: {len(continue_lines)}")

    if len(continue_lines) == 1:
        print("✅ PASS: Exactly one continue message from wrapper")
        return True
    print(f"❌ FAIL: Expected 1 continue message, got {len(continue_lines)}")
    print("Output:")
    for i, line in enumerate(output_lines, 1):
        print(f"  {i}: {line}")
    return False


if __name__ == "__main__":
    print("Testing Hook Continue Message Fix")
    print("=" * 50)

    # Test direct handler
    handler_pass = test_hook_handler()

    # Test wrapper + handler
    wrapper_pass = test_hook_wrapper()

    print("\n" + "=" * 50)
    if handler_pass and wrapper_pass:
        print("✅ ALL TESTS PASSED")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        sys.exit(1)
