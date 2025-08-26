#!/usr/bin/env python3
"""Demo script to show how agent events appear in the monitoring system."""

import subprocess
import time
import webbrowser
from pathlib import Path


def main():
    print("🤖 Agent Event Demonstration")
    print("=" * 50)

    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"

    print("\n1. Opening dashboard...")
    webbrowser.open(dashboard_url)
    time.sleep(2)

    print("\n2. Running Claude with agent delegation prompts...")

    # Test different types of agent delegations
    test_prompts = [
        {
            "prompt": "Create a simple hello world Python script",
            "desc": "Basic task (no agent delegation expected)",
        },
        {
            "prompt": "Use the Task tool to ask the research agent to find information about Python decorators",
            "desc": "Explicit Task tool usage",
        },
    ]

    for i, test in enumerate(test_prompts, 1):
        print(f"\n   Test {i}: {test['desc']}")
        print(f"   Prompt: {test['prompt'][:60]}...")

        # Run the command
        cmd = [
            "python",
            "-m",
            "claude_mpm",
            "run",
            "-i",
            test["prompt"],
            "--non-interactive",
        ]

        result = subprocess.run(
            cmd, cwd=Path(__file__).parent.parent, capture_output=True, text=True, check=False
        )

        if result.returncode == 0:
            print("   ✅ Command completed")
        else:
            print(f"   ❌ Error: {result.stderr[:100]}")

        time.sleep(2)

    print("\n3. Check the dashboard for:")
    print("   - Look for 'hook' type events in the event list")
    print("   - Filter by 'Hook' to see only hook events")
    print("   - Look for events with tool_name='Task'")
    print("   - Check the event details for agent information")

    print("\n4. What to look for in Task tool events:")
    print("   - subagent_type: The type of agent (research, engineer, pm, etc.)")
    print("   - description: What the agent is asked to do")
    print("   - prompt: The full prompt sent to the agent")
    print("   - delegation_details: Additional information about the delegation")

    print("\n5. Agent-related events to watch for:")
    print("   - hook.pre_tool (with tool_name='Task') - Agent delegation starting")
    print("   - hook.post_tool (with tool_name='Task') - Agent delegation completed")
    print("   - hook.subagent_stop - Agent execution stopped")

    print("\n✅ Demo complete! Check the dashboard for agent events.")


if __name__ == "__main__":
    main()
