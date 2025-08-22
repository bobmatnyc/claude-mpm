#!/usr/bin/env python3
"""Test that PM instructions properly reference the Ticketing Agent."""

import sys
from pathlib import Path


def test_ticketing_instructions():
    """Verify ticketing agent guidance is in PM instructions."""
    print("Testing Ticketing Agent Instructions")
    print("=" * 50)

    # Read the INSTRUCTIONS.md file
    instructions_path = (
        Path(__file__).parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "INSTRUCTIONS.md"
    )

    if not instructions_path.exists():
        print(f"❌ Instructions file not found at: {instructions_path}")
        return False

    content = instructions_path.read_text()

    # Check for key ticketing references
    checks = [
        (
            "Ticketing Agent mentioned in Context-Aware Selection",
            "**Ticket/issue management** → Ticketing Agent" in content,
        ),
        (
            "Ticketing Agent Scenarios section exists",
            "### Ticketing Agent Scenarios" in content,
        ),
        (
            "Ticket keyword triggers listed",
            '"ticket", "tickets", "ticketing"' in content,
        ),
        ("Epic keyword triggers listed", '"epic", "epics"' in content),
        ("Issue keyword triggers listed", '"issue", "issues"' in content),
        ("Task tracking mentioned", '"task tracking", "task management"' in content),
        (
            "Ticketing specializations listed",
            "Creating and managing epics, issues, and tasks" in content,
        ),
    ]

    print("\nChecking PM Instructions for Ticketing Agent guidance:")
    print("-" * 50)

    all_passed = True
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"{status} {check_name}")
        if not passed:
            all_passed = False

    print("-" * 50)

    # Also verify the ticketing agent exists
    ticketing_agent_path = Path.cwd() / ".claude" / "agents" / "ticketing.md"
    if ticketing_agent_path.exists():
        print("\n✓ Ticketing Agent is deployed at: .claude/agents/ticketing.md")
    else:
        print("\n✗ Ticketing Agent NOT found at: .claude/agents/ticketing.md")
        all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("✅ SUCCESS: PM Instructions properly configured for Ticketing Agent")
        print("\nThe PM will now delegate to Ticketing Agent when users mention:")
        print("  - tickets, ticketing")
        print("  - epics")
        print("  - issues")
        print("  - task tracking/management")
        print("  - project documentation")
        print("  - work breakdown")
        print("  - user stories")
    else:
        print("❌ FAILURE: Some checks failed")

    return all_passed


if __name__ == "__main__":
    success = test_ticketing_instructions()
    sys.exit(0 if success else 1)