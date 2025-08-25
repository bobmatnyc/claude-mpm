#!/usr/bin/env python3
"""Test script to verify agent information is captured in hooks."""

import subprocess
import sys
import time
from pathlib import Path


def main():
    print("🔍 Testing agent information in hooks...")

    # Start monitoring
    print("\n1. Starting Socket.IO monitoring server...")
    monitor_process = subprocess.Popen(
        [sys.executable, "-m", "claude_mpm", "--monitor"],
        cwd=Path(__file__).parent.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Give server time to start
    time.sleep(2)

    # Create a test file that will trigger agent delegation
    test_file = Path(__file__).parent / "test_agent_delegation.py"
    test_content = '''#!/usr/bin/env python3
"""
This is a test file to trigger agent delegation.
We'll ask Claude to use different agents to analyze this code.
"""

def calculate_fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

def main():
    # Test the function
    for i in range(10):
        print(f"Fibonacci({i}) = {calculate_fibonacci(i)}")

if __name__ == "__main__":
    main()
'''

    print("\n2. Creating test file for agent analysis...")
    test_file.write_text(test_content)

    # Create prompts that will trigger different agent delegations
    prompts = [
        "Use the research agent to analyze the efficiency of the fibonacci function in test_agent_delegation.py",
        "Use the engineer agent to optimize the fibonacci function for better performance",
        "Use the pm agent to create a plan for improving this code's documentation",
        "Use the Task tool to delegate to the qa agent to write tests for this function",
    ]

    print("\n3. Running Claude with agent delegation prompts...")
    for i, prompt in enumerate(prompts, 1):
        print(f"\n   Prompt {i}: {prompt[:60]}...")

        # Run Claude with the prompt
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "claude_mpm",
                "run",
                "-i",
                prompt,
                "--non-interactive",
            ],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            print(f"   ❌ Error: {result.stderr}")
        else:
            print("   ✅ Success")

        # Give time for events to be processed
        time.sleep(1)

    print("\n4. Checking for agent-related events...")
    print("\n   Expected events:")
    print("   - PreToolUse events with tool_name='Task'")
    print("   - delegation_details with agent_type, prompt, description")
    print("   - SubagentStop events when agents complete")

    print("\n5. Open the dashboard to view agent events:")
    print(
        f"   file://{Path(__file__).parent / 'claude_mpm_socketio_dashboard.html'}?autoconnect=true"
    )

    print("\n6. Look for:")
    print("   - Hook events with 'Task' tool usage")
    print("   - Agent delegation details in the event data")
    print("   - SubagentStop events showing agent completion")

    print("\nPress Ctrl+C to stop monitoring...")

    try:
        monitor_process.wait()
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor_process.terminate()
        monitor_process.wait()

        # Clean up test file
        if test_file.exists():
            test_file.unlink()
            print("Cleaned up test file.")


if __name__ == "__main__":
    main()
