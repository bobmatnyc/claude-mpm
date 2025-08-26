#!/usr/bin/env python3
"""Test the Claude hook flow with proper event format.

This script tests the complete flow from Claude hook events to dashboard.
It simulates how Claude actually sends events to the hook handler.
"""

import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def find_hook_handler():
    """Find the hook handler script."""
    # Check common locations
    locations = [
        Path.home() / ".claude/hooks/claude_hooks/hook_handler.py",
        Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py",
    ]

    for path in locations:
        if path.exists():
            return path

    # Try to find via claude-mpm
    try:
        result = subprocess.run(
            ["claude-mpm", "hook", "--show-path"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            hook_path = Path(result.stdout.strip()) / "claude_hooks/hook_handler.py"
            if hook_path.exists():
                return hook_path
    except Exception:
        pass

    return None

def test_hook_event(event_data):
    """Send an event to the hook handler and check the result."""
    hook_handler = find_hook_handler()
    if not hook_handler:
        print("❌ Could not find hook handler")
        return False

    print(f"Using hook handler: {hook_handler}")

    # Convert event to JSON
    event_json = json.dumps(event_data)

    # Run the hook handler with the event
    try:
        result = subprocess.run(
            [sys.executable, str(hook_handler)],
            input=event_json,
            capture_output=True,
            text=True,
            timeout=5, check=False
        )

        # Check if we got the expected continue response
        if result.stdout.strip():
            response = json.loads(result.stdout.strip())
            if response.get("action") == "continue":
                print("✅ Hook handler responded with continue")
                return True
            print(f"❌ Unexpected response: {response}")
            return False
        print("❌ No response from hook handler")
        if result.stderr:
            print(f"Stderr: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("❌ Hook handler timed out")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON response: {e}")
        print(f"Stdout: {result.stdout}")
        return False
    except Exception as e:
        print(f"❌ Error running hook handler: {e}")
        return False

def main():
    """Test various Claude hook events."""
    print("\n" + "="*60)
    print("Testing Claude Hook Event Flow")
    print("="*60)

    # Test 1: UserPromptSubmit event
    print("\n1. Testing UserPromptSubmit event...")
    user_prompt_event = {
        "hook_event_name": "UserPromptSubmit",
        "prompt": "Write a Python function to calculate fibonacci numbers",
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(user_prompt_event):
        print("✅ UserPromptSubmit event processed successfully")
    else:
        print("❌ UserPromptSubmit event failed")

    time.sleep(1)

    # Test 2: PreToolUse event
    print("\n2. Testing PreToolUse event...")
    pre_tool_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Read",
        "tool_input": {
            "file_path": "/Users/test/example.py"
        },
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(pre_tool_event):
        print("✅ PreToolUse event processed successfully")
    else:
        print("❌ PreToolUse event failed")

    time.sleep(1)

    # Test 3: PreToolUse with Task delegation
    print("\n3. Testing PreToolUse event with Task delegation...")
    task_event = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Task",
        "tool_input": {
            "subagent_type": "research",
            "prompt": "Analyze the codebase architecture",
            "description": "Provide a comprehensive analysis of the project structure"
        },
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(task_event):
        print("✅ Task delegation event processed successfully")
    else:
        print("❌ Task delegation event failed")

    time.sleep(1)

    # Test 4: PostToolUse event
    print("\n4. Testing PostToolUse event...")
    post_tool_event = {
        "hook_event_name": "PostToolUse",
        "tool_name": "Read",
        "exit_code": 0,
        "tool_output": "File content here...",
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(post_tool_event):
        print("✅ PostToolUse event processed successfully")
    else:
        print("❌ PostToolUse event failed")

    time.sleep(1)

    # Test 5: SubagentStop event
    print("\n5. Testing SubagentStop event...")
    subagent_stop_event = {
        "hook_event_name": "SubagentStop",
        "agent_type": "research",
        "reason": "completed",
        "output": "Analysis complete. The codebase follows a modular architecture...",
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(subagent_stop_event):
        print("✅ SubagentStop event processed successfully")
    else:
        print("❌ SubagentStop event failed")

    time.sleep(1)

    # Test 6: Stop event
    print("\n6. Testing Stop event...")
    stop_event = {
        "hook_event_name": "Stop",
        "reason": "completed",
        "session_id": f"test-session-{int(time.time())}",
        "cwd": str(Path.cwd()),
        "timestamp": datetime.now().isoformat()
    }

    if test_hook_event(stop_event):
        print("✅ Stop event processed successfully")
    else:
        print("❌ Stop event failed")

    print("\n" + "="*60)
    print("Test Complete!")
    print("Check the dashboard at http://localhost:8765/dashboard")
    print("You should see the events appearing in real-time")
    print("="*60)

if __name__ == "__main__":
    main()
