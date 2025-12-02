#!/usr/bin/env python3
"""Test the updated agent capabilities generation."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.management.agent_capabilities_generator import \
    AgentCapabilitiesGenerator
from claude_mpm.services.agents.registry.deployed_agent_discovery import \
    DeployedAgentDiscovery


def test_capabilities_generation():
    """Test that capabilities are correctly generated with both name and ID."""
    print("Testing Updated Agent Capabilities Generation")
    print("=" * 60)

    # Test 1: DeployedAgentDiscovery
    print("\n1. Testing DeployedAgentDiscovery...")
    discovery = DeployedAgentDiscovery()
    agents = discovery.discover_deployed_agents()

    if agents:
        print(f"   ✓ Found {len(agents)} deployed agents")
        for agent in agents[:3]:  # Show first 3
            print(f"      - {agent['name']} (id: {agent['id']})")
    else:
        print("   ⚠ No agents found")

    # Test 2: AgentCapabilitiesGenerator
    print("\n2. Testing AgentCapabilitiesGenerator...")
    generator = AgentCapabilitiesGenerator()
    capabilities_content = generator.generate_capabilities_section(agents)

    print("   Generated content preview:")
    print("   " + "-" * 50)
    for line in capabilities_content.split("\n")[:20]:  # Show first 20 lines
        print(f"   {line}")
    print("   " + "-" * 50)

    # Check for key elements
    checks = [
        ("Agent names with IDs", "(`" in capabilities_content),
        (
            "Engineering Agents section",
            "### Engineering Agents" in capabilities_content
            or "engineer" in capabilities_content,
        ),
        (
            "Research Agents section",
            "### Research Agents" in capabilities_content
            or "research" in capabilities_content,
        ),
        ("Total agents count", "Total Available Agents" in capabilities_content),
        ("Task tool instruction", "agent ID in parentheses" in capabilities_content),
    ]

    print("\n   Content validation:")
    for check_name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"   {status} {check_name}")

    # Test 3: FrameworkLoader
    print("\n3. Testing FrameworkLoader capabilities generation...")
    loader = FrameworkLoader()
    framework_capabilities = loader._generate_agent_capabilities_section()

    print("   Framework loader content preview:")
    print("   " + "-" * 50)
    for line in framework_capabilities.split("\n")[:15]:  # Show first 15 lines
        print(f"   {line}")
    print("   " + "-" * 50)

    # Check framework loader output
    framework_checks = [
        ("Agent IDs in parentheses", "(`" in framework_capabilities),
        ("Clean agent names", "**" in framework_capabilities),
        (
            "Usage instructions",
            "Task tool" in framework_capabilities
            or "delegating tasks" in framework_capabilities,
        ),
    ]

    print("\n   Framework loader validation:")
    for check_name, passed in framework_checks:
        status = "✓" if passed else "✗"
        print(f"   {status} {check_name}")

    print("\n" + "=" * 60)
    print("Test Summary:")
    all_passed = all(check[1] for check in checks) and all(
        check[1] for check in framework_checks
    )
    if all_passed:
        print("✅ All tests passed! The agent capabilities now show both:")
        print("   - Clean agent names (for TodoWrite)")
        print("   - Agent IDs in parentheses (for Task tool)")
        return True
    print("⚠️ Some tests failed. Please review the output above.")
    return False


if __name__ == "__main__":
    success = test_capabilities_generation()
    sys.exit(0 if success else 1)
