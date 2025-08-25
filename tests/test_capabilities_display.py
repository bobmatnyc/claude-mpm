#!/usr/bin/env python3
"""Test that memory routing appears in agent capabilities display."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader


def test_capabilities_display():
    """Test that memory routing appears in capabilities."""

    print("Testing Memory Routing in Agent Capabilities")
    print("=" * 50)

    # Initialize framework loader
    framework_loader = FrameworkLoader()

    # Parse metadata for a deployed agent
    test_agent_file = Path(".claude/agents/engineer.md")

    if test_agent_file.exists():
        print(f"\n1. Testing metadata parsing for {test_agent_file}:")
        metadata = framework_loader._parse_agent_metadata(test_agent_file)

        if metadata:
            print(f"  Agent ID: {metadata.get('id', 'Unknown')}")
            print(f"  Has routing: {'routing' in metadata}")
            print(f"  Has memory_routing: {'memory_routing' in metadata}")

            if "memory_routing" in metadata:
                mr = metadata["memory_routing"]
                print(
                    f"  Memory routing description: {mr.get('description', 'None')[:60]}..."
                )
                print(f"  Categories: {len(mr.get('categories', []))}")
                print(f"  Keywords: {len(mr.get('keywords', []))}")
            else:
                print("  ✗ No memory_routing found in metadata")
        else:
            print("  ✗ Could not parse metadata")
    else:
        print(f"  ✗ Agent file not found: {test_agent_file}")

    # Check the generated capabilities section
    print("\n2. Checking generated capabilities section:")
    capabilities = framework_loader._generate_agent_capabilities_section()

    # Look for specific agents and their memory routing
    test_agents = ["engineer", "research", "qa", "security", "documentation"]

    for agent in test_agents:
        # Look for the agent section
        agent_section_start = capabilities.find("### ")
        if agent_section_start != -1:
            # Find this specific agent
            agent_marker = f"(`{agent}`)"
            if agent_marker in capabilities:
                print(f"\n  Agent: {agent}")
                # Check if memory routing appears after this agent
                agent_pos = capabilities.find(agent_marker)
                next_agent_pos = capabilities.find("### ", agent_pos + 1)
                if next_agent_pos == -1:
                    next_agent_pos = len(capabilities)

                agent_section = capabilities[agent_pos:next_agent_pos]

                if "Memory Routing:" in agent_section:
                    print("    ✓ Has memory routing info")
                    # Extract the memory routing line
                    mr_start = agent_section.find("Memory Routing:")
                    mr_end = agent_section.find("\n", mr_start)
                    if mr_end != -1:
                        mr_line = agent_section[mr_start:mr_end]
                        print(f"    {mr_line[:80]}...")
                else:
                    print("    ✗ No memory routing info")

    # Show a sample of the capabilities output
    print("\n3. Sample of capabilities output:")
    print("-" * 40)
    # Find first agent with memory routing
    if "Memory Routing:" in capabilities:
        mr_pos = capabilities.find("Memory Routing:")
        start = max(0, mr_pos - 200)
        end = min(len(capabilities), mr_pos + 200)
        print(capabilities[start:end])
    else:
        # Show first agent section
        agent_start = capabilities.find("### ")
        if agent_start != -1:
            print(capabilities[agent_start : min(agent_start + 500, len(capabilities))])

    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_capabilities_display()
