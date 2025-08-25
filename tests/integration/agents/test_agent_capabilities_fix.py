#!/usr/bin/env python3
"""Test script to verify that agent capabilities discovery shows correct agent IDs.

This script verifies that:
1. Agent IDs are read from deployed .claude/agents/*.md files
2. The IDs match the filenames (without .md extension)
3. The PM context shows these exact IDs for Task tool delegation
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_agent_capabilities_discovery():
    """Test that agent capabilities are correctly discovered from deployed agents."""
    print("Testing Agent Capabilities Discovery Fix")
    print("=" * 50)

    # Check deployed agents directory
    agents_dir = Path.cwd() / ".claude" / "agents"
    if not agents_dir.exists():
        print(f"❌ No .claude/agents directory found at {agents_dir}")
        return False

    # List deployed agents
    print("\n✅ Found .claude/agents directory")
    print("\nDeployed agents (these should be the agent IDs):")
    deployed_ids = []
    for agent_file in sorted(agents_dir.glob("*.md")):
        if not agent_file.name.startswith("."):
            agent_id = agent_file.stem
            deployed_ids.append(agent_id)
            print(f"  - {agent_id} (from {agent_file.name})")

    # Initialize framework loader
    print("\n" + "=" * 50)
    print("Testing Framework Loader Agent Discovery")
    print("=" * 50)

    loader = FrameworkLoader()

    # Get the capabilities section
    capabilities_section = loader._generate_agent_capabilities_section()

    # Check that the section contains correct agent IDs
    print("\nGenerated capabilities section preview:")
    print("-" * 40)
    # Show first 1500 chars of the section
    preview = (
        capabilities_section[:1500]
        if len(capabilities_section) > 1500
        else capabilities_section
    )
    print(preview)
    if len(capabilities_section) > 1500:
        print("... [truncated]")
    print("-" * 40)

    # Verify that deployed agent IDs appear in the capabilities section
    print("\nVerifying agent IDs in capabilities section:")
    issues = []
    successes = []

    for agent_id in deployed_ids:
        # Check for the exact ID in backticks (the format we use)
        if f"`{agent_id}`" in capabilities_section:
            successes.append(agent_id)
            print(f"  ✅ {agent_id} - Found with correct format")
        # Check if it appears with wrong format
        elif f"{agent_id}_agent" in capabilities_section:
            issues.append(f"{agent_id} appears as {agent_id}_agent (wrong format)")
            print(f"  ❌ {agent_id} - Found but with '_agent' suffix (wrong)")
        elif agent_id.replace("_", " ").title() in capabilities_section:
            issues.append(f"{agent_id} appears only as title case (missing ID)")
            print(f"  ⚠️  {agent_id} - Found as name only, missing backtick ID")
        else:
            issues.append(f"{agent_id} not found at all")
            print(f"  ❌ {agent_id} - Not found in capabilities")

    # Check for important usage instructions
    print("\n" + "=" * 50)
    print("Checking Usage Instructions")
    print("=" * 50)

    has_usage_note = (
        "IMPORTANT" in capabilities_section and "exact agent ID" in capabilities_section
    )
    if has_usage_note:
        print("✅ Contains usage instructions about using exact agent IDs")
    else:
        print("❌ Missing usage instructions about exact agent IDs")
        issues.append("Missing usage instructions")

    # Summary
    print("\n" + "=" * 50)
    print("Test Summary")
    print("=" * 50)
    print(f"Total deployed agents: {len(deployed_ids)}")
    print(f"Correctly formatted: {len(successes)}")
    print(f"Issues found: {len(issues)}")

    if issues:
        print("\nIssues to fix:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    print(
        "\n✅ All tests passed! Agent IDs are correctly discovered and formatted."
    )
    print("\nThe PM context will now show agent IDs that work with the Task tool:")
    print("  - Use `research` not `research_agent`")
    print("  - Use `engineer` not `engineer_agent`")
    print("  - etc.")
    return True


if __name__ == "__main__":
    success = test_agent_capabilities_discovery()
    sys.exit(0 if success else 1)
