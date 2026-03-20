#!/usr/bin/env python3
"""Test script to verify agent deduplication fix in framework_loader.py"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import logging

from claude_mpm.core.framework_loader import FrameworkLoader

# Set up logging to see detailed output
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def test_agent_deduplication():
    """Test the agent deduplication functionality"""
    print("=== Testing Agent Deduplication Fix ===\n")

    # Initialize framework loader
    loader = FrameworkLoader()

    print("1. BASIC FUNCTIONALITY TEST")
    print("-" * 40)

    # Test that framework loads successfully
    instructions = loader.get_framework_instructions()

    # Check if agents section is present
    if "Available Agent Capabilities" in instructions:
        print("✅ Agent capabilities section found")
    else:
        print("❌ Agent capabilities section missing")
        return False

    print("\n2. DEDUPLICATION TEST")
    print("-" * 40)

    # Look for QA agents specifically in the agent capabilities section
    lines = instructions.split("\n")
    in_capabilities_section = False
    qa_agent_definitions = []

    for i, line in enumerate(lines):
        if "## Available Agent Capabilities" in line:
            in_capabilities_section = True
            continue
        # Exit capabilities section when we hit another main section (starting with ##, not ###)
        if (
            in_capabilities_section
            and line.startswith("## ")
            and "Agent Capabilities" not in line
        ):
            in_capabilities_section = False
            continue

        if (
            in_capabilities_section
            and line.startswith("### ")
            and line.lower().startswith("### qa ")
        ):
            qa_agent_definitions.append((i, line.strip()))

    print(
        f"Found {len(qa_agent_definitions)} QA agent definitions in capabilities section:"
    )
    for line_num, line in qa_agent_definitions:
        print(f"  Line {line_num}: {line}")

    # Should only have one QA agent definition (project overrides user)
    if len(qa_agent_definitions) == 1:
        print("✅ QA agent deduplication working correctly")

        # Check if it's the project agent
        if "PROJECT QA Agent" in instructions:
            print("✅ Project QA agent correctly overrode user QA agent")
        else:
            print("⚠️  Could not verify project QA agent content")
    else:
        print("❌ QA agent deduplication failed - found multiple agent definitions")
        return False

    print("\n3. HIERARCHY VERIFICATION")
    print("-" * 40)

    # Check logs to see which agents were loaded
    # This will be in the debug output above

    print("Check the debug logs above to verify:")
    print("- Project agents are loaded with priority 0")
    print("- User agents are loaded with priority 1")
    print("- Project qa.md overrides user qa.md")

    print("\n4. AGENT COUNT VERIFICATION")
    print("-" * 40)

    # Count total agents mentioned
    agent_sections = []
    for line in lines:
        if line.startswith("### ") and "(`" in line and "`)" in line:
            agent_sections.append(line)

    print(f"Total unique agents found: {len(agent_sections)}")
    for agent in agent_sections:
        print(f"  {agent}")

    # Should have 14 user agents + 1 project qa override = 15 total (no duplicates)
    expected_count = 15  # 14 unique user agents + 1 project qa agent
    if len(agent_sections) == expected_count:
        print(f"✅ Agent count correct: {expected_count} unique agents")
    else:
        print(
            f"❌ Agent count incorrect: expected {expected_count}, got {len(agent_sections)}"
        )
        return False

    print("\n=== ALL TESTS PASSED ===")
    return None


if __name__ == "__main__":
    success = test_agent_deduplication()
    sys.exit(0 if success else 1)
