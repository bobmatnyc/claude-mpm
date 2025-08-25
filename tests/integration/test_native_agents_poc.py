#!/usr/bin/env python3
"""POC1: Test native agent recognition and delegation."""

import os
import shlex
import subprocess
from pathlib import Path


def run_test(test_name, command):
    """Run a test command and capture output."""
    print(f"\n🧪 Test: {test_name}")
    print("-" * 60)
    print(f"Command: {command}")
    print("-" * 60)

    # Split command string into a list to avoid shell=True
    command_parts = shlex.split(command)
    result = subprocess.run(
        command_parts, capture_output=True, text=True, cwd=Path(__file__).parent.parent, check=False
    )

    print("Output:")
    print(result.stdout)

    if result.stderr:
        print("\nErrors:")
        print(result.stderr)

    return result.returncode == 0, result.stdout, result.stderr


def main():
    print("🔬 POC1: Native Agent Recognition and Delegation Test")
    print("=" * 80)

    # Ensure we're in the right directory
    os.chdir(Path(__file__).parent.parent)

    # Test 1: Deploy agents
    print("\n📦 Deploying agents...")
    deploy_result = subprocess.run(
        [
            "python",
            "scripts/launch_with_agents.py",
            "--force",
            "--non-interactive",
            "list agents",
        ],
        capture_output=True,
        text=True, check=False,
    )

    if "Deployed" in deploy_result.stdout:
        print("✅ Agents deployed successfully")
    else:
        print("❌ Agent deployment may have failed")

    # Test 2: List agents
    success, output, _ = run_test(
        "List Available Agents",
        'python scripts/launch_with_agents.py --non-interactive "Please list all available agents you can delegate tasks to"',
    )

    agents_found = []
    for agent in ["engineer", "qa", "documentation", "research", "security", "ops"]:
        if agent in output.lower():
            agents_found.append(agent)

    print(f"\n✅ Agents found in response: {agents_found}")

    # Test 3: Simple delegation
    success, output, _ = run_test(
        "Simple Delegation Test",
        'python scripts/launch_with_agents.py --non-interactive "Delegate to engineer: Create a simple hello world function"',
    )

    delegation_worked = "Task(" in output or "delegat" in output.lower()

    # Test 4: Multi-agent delegation
    success, output, _ = run_test(
        "Multi-Agent Delegation",
        '''python scripts/launch_with_agents.py --non-interactive "Please delegate these tasks:
1. engineer: Create a factorial function
2. qa: Write tests for the factorial function
3. documentation: Document the factorial function"''',
    )

    # Summary
    print("\n" + "=" * 80)
    print("📊 POC1 Test Summary")
    print("=" * 80)

    print(f"\n✅ Agents deployed: {Path('.claude/agents').exists()}")
    print(f"✅ Agents recognized: {len(agents_found)} found")
    print(f"✅ Delegation works: {delegation_worked}")

    # Check actual files
    agent_files = list(Path(".claude/agents").glob("*.md"))
    print("\n📁 Agent files in .claude/agents/:")
    for f in agent_files:
        print(f"  - {f.name}")

    print("\n🎯 Conclusion:")
    if len(agents_found) > 0 and delegation_worked:
        print("✅ SUCCESS: Native agents are recognized and delegation is working!")
        print("The framework can now use Claude's native subagent feature.")
    else:
        print("⚠️  PARTIAL SUCCESS: Agents deployed but delegation needs testing")
        print("Try running manually: python scripts/launch_with_agents.py")


if __name__ == "__main__":
    main()
