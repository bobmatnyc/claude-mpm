#!/usr/bin/env python3
"""Verify TodoWrite format consistency across PM and agent templates."""

import sys
from pathlib import Path


def check_todowrite_format():
    """Check that TodoWrite format is consistent across templates."""

    # Read BASE_AGENT_TEMPLATE.md
    agent_template_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "BASE_AGENT_TEMPLATE.md"
    )
    agent_content = agent_template_path.read_text()

    # Read BASE_PM.md
    pm_template_path = (
        Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
    )
    pm_content = pm_template_path.read_text()

    # Check for correct format in agent template
    print("✓ Checking BASE_AGENT_TEMPLATE.md...")

    # Should use [Agent] format, not TODO (Priority): format
    if (
        "TODO (High Priority):" in agent_content
        or "TODO (Medium Priority):" in agent_content
    ):
        print("  ❌ Found old TODO format in agent template")
        return False

    if "[Agent] Task description" in agent_content or "[Engineer]" in agent_content:
        print("  ✓ Agent template uses correct [Agent] format")
    else:
        print("  ❌ Agent template missing [Agent] format examples")
        return False

    # Check PM template has TodoWrite rules
    print("✓ Checking BASE_PM.md...")
    if "[Agent]" in pm_content and "TodoWrite" in pm_content:
        print("  ✓ PM template has TodoWrite rules with [Agent] format")
    else:
        print("  ❌ PM template missing TodoWrite rules")
        return False

    # Check specific agents like engineer.md if they exist
    engineer_path = Path(__file__).parent.parent / ".claude" / "agents" / "engineer.md"
    if engineer_path.exists():
        print("✓ Checking deployed engineer.md...")
        engineer_content = engineer_path.read_text()
        if "[Engineer]" in engineer_content:
            print("  ✓ Engineer agent uses correct [Engineer] format")
        else:
            print("  ⚠️ Engineer agent may need format update")

    print("\n✅ TodoWrite format verification complete!")
    return True


if __name__ == "__main__":
    success = check_todowrite_format()
    sys.exit(0 if success else 1)
