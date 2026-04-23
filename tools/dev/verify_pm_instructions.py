#!/usr/bin/env python3
"""Verify PM instructions contain correct agent IDs after the fix."""

import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def verify_pm_instructions():
    """Verify the PM instructions use correct agent IDs."""

    loader = FrameworkLoader()
    pm_instructions = loader.get_framework_instructions()

    print("Verifying PM Instructions")
    print("=" * 50)

    # Check for correct agent IDs
    correct_ids = [
        "research-agent",
        "qa-agent",
        "documentation-agent",
        "security-agent",
        "data-engineer",
        "ops-agent",
        "version-control",
    ]

    print("\nChecking for correct agent IDs in PM instructions:")
    for agent_id in correct_ids:
        if f"`{agent_id}`" in pm_instructions:
            print(f"✓ Found: {agent_id}")
        else:
            print(f"✗ Missing: {agent_id}")

    # Extract all backtick-wrapped IDs
    agent_ids = re.findall(r"`([^`]+)`", pm_instructions)

    # Filter to only agent-like IDs (containing 'agent' or known patterns)
    agent_like_ids = [
        aid
        for aid in agent_ids
        if "agent" in aid or aid in ["engineer", "data-engineer", "version-control"]
    ]

    print("\nAll agent IDs found in PM instructions:")
    for aid in sorted(set(agent_like_ids)):
        print(f"  - {aid}")

    # Check for Task tool examples
    print("\nChecking Task tool usage examples:")
    lines = pm_instructions.split("\n")
    task_examples = []

    for _i, line in enumerate(lines):
        if "subagent_type" in line:
            task_examples.append(line.strip())

    if task_examples:
        print("✓ Found Task tool examples with subagent_type:")
        for ex in task_examples[:5]:  # Show first 5 examples
            print(f"  {ex}")
    else:
        print("✗ No Task tool examples found")

    # Verify no old IDs are used as agent IDs
    old_ids = ["research", "qa", "documentation", "security", "ops"]
    print("\nVerifying old IDs are not used as agent IDs:")
    for old_id in old_ids:
        # Check if old ID appears as a standalone agent ID
        if (
            f"`{old_id}`" in pm_instructions
            and f"`{old_id}-agent`" not in pm_instructions
        ):
            print(f"✗ Old ID still in use: {old_id}")
        else:
            print(f"✓ Old ID not used: {old_id}")

    print("\n" + "=" * 50)
    print("Verification complete!")


if __name__ == "__main__":
    verify_pm_instructions()
