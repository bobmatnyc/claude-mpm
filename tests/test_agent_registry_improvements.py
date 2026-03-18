#!/usr/bin/env python3
"""Test script to verify agent registry improvements."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.core.agent_registry import AgentRegistryAdapter


def test_agent_registry():
    """Test the improved agent registry functionality."""
    print("Testing Agent Registry Improvements\n" + "=" * 40)

    # Initialize registry
    print("\n1. Initializing Agent Registry...")
    registry = AgentRegistryAdapter()

    # List all agents
    print("\n2. Listing all agents:")
    agents = registry.list_agents()
    print(f"   Found {len(agents)} agents")

    # Show agent details
    print("\n3. Agent Details:")
    for agent_key, metadata in agents.items():
        print(f"\n   {agent_key}:")
        print(f"   - ID: {metadata.get('id')}")
        print(f"   - Type: {metadata.get('type')}")
        print(f"   - Tier: {metadata.get('tier')}")
        print(f"   - Name: {metadata.get('name')}")
        print(f"   - Nickname: {metadata.get('nickname')}")
        print(f"   - Specializations: {metadata.get('specializations', [])}")

    # Test agent hierarchy
    print("\n4. Agent Hierarchy:")
    hierarchy = registry.get_agent_hierarchy()
    for tier, agent_list in hierarchy.items():
        print(
            f"   {tier.capitalize()}: {len(agent_list)} agents - {', '.join(agent_list)}"
        )

    # Test health check - not available in adapter
    print("\n5. Registry Health Check:")
    print("   Health check not available in adapter")

    # Test agent selection
    print("\n6. Agent Selection Tests:")
    test_tasks = [
        ("Implement user authentication", ["security", "authentication"]),
        ("Write unit tests", ["testing", "qa"]),
        ("Create documentation", ["documentation", "writing"]),
        ("Deploy to production", ["deployment", "operations"]),
        ("Investigate performance issue", ["research", "performance"]),
    ]

    for task, specializations in test_tasks:
        selected = registry.select_agent_for_task(task, specializations)
        if selected:
            print(f"   Task: '{task}'")
            print(f"   Selected: {selected['id']} ({selected['metadata']['name']})")
        else:
            print(f"   Task: '{task}' - No agent found")

    # Test Task Tool formatting
    print("\n7. Task Tool Formatting:")
    formatted = registry.format_agent_for_task_tool(
        "engineer", "Implement JWT authentication", "Use best practices for security"
    )
    if formatted:
        print(formatted)
    else:
        print("   No formatting available")

    # Test mapping between JSON keys and file names
    print("\n8. Agent ID Mapping Verification:")
    expected_mappings = {
        "operations": "ops-agent.md",
        "version_control": "version-control-agent.md",
        "architect": "pm-orchestrator-agent.md",
    }

    for json_key, _expected_file in expected_mappings.items():
        if json_key in agents:
            print(f"   ✓ {json_key} correctly mapped")
        else:
            print(f"   ✗ {json_key} NOT found in registry")

    print("\n" + "=" * 40)
    print("Agent Registry Test Complete!")


if __name__ == "__main__":
    test_agent_registry()
