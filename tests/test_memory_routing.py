#!/usr/bin/env python3
"""Test script to verify dynamic memory routing implementation."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.memory.router import MemoryRouter


def test_memory_routing():
    """Test that memory routing patterns are loaded correctly."""

    print("Testing Dynamic Memory Routing Implementation")
    print("=" * 50)

    # Test 1: Framework loader can load memory routing
    print("\n1. Testing Framework Loader:")
    framework_loader = FrameworkLoader()

    # Test loading memory routing for a few agents
    test_agents = ["engineer", "research", "qa", "security", "documentation"]

    for agent in test_agents:
        memory_routing = framework_loader._load_memory_routing_from_template(agent)
        if memory_routing:
            print(
                f"  ✓ {agent}: Found memory routing - {memory_routing.get('description', 'No description')[:60]}..."
            )
        else:
            print(f"  ✗ {agent}: No memory routing found")

    # Test 2: Memory router uses dynamic patterns
    print("\n2. Testing Memory Router:")
    router = MemoryRouter()

    # Get routing patterns
    patterns = router.get_routing_patterns()

    print(f"  Total agents: {len(patterns['agents'])}")
    print(f"  Static agents: {len(patterns.get('static_agents', []))}")
    print(f"  Dynamic agents: {len(patterns.get('dynamic_agents', []))}")

    # Test 3: Test routing some sample content
    print("\n3. Testing Content Routing:")

    test_cases = [
        {
            "content": "Remember to use dependency injection and SOLID principles in all implementations",
            "expected": "engineer",
        },
        {
            "content": "Remember the analysis findings about the authentication architecture",
            "expected": "research",
        },
        {
            "content": "Remember to always run pytest with coverage before committing",
            "expected": "qa",
        },
        {
            "content": "Remember to check for OWASP vulnerabilities and use encryption",
            "expected": "security",
        },
        {
            "content": "Remember to update the API documentation and user guide",
            "expected": "documentation",
        },
    ]

    for test in test_cases:
        result = router.analyze_and_route(test["content"])
        target = result["target_agent"]
        confidence = result["confidence"]

        if target == test["expected"]:
            print(f"  ✓ Routed to {target} (confidence: {confidence:.2f}) - CORRECT")
        else:
            print(
                f"  ✗ Routed to {target} instead of {test['expected']} (confidence: {confidence:.2f})"
            )
            print(f"    Reasoning: {result['reasoning']}")

    # Test 4: Check if memory routing info would appear in capabilities
    print("\n4. Testing Agent Capabilities Display:")

    # This simulates what the PM would see
    capabilities_section = framework_loader._generate_agent_capabilities_section()

    # Check if memory routing appears in the output
    if "Memory Routing:" in capabilities_section:
        print("  ✓ Memory routing information appears in agent capabilities")

        # Count how many agents have memory routing
        count = capabilities_section.count("Memory Routing:")
        print(f"  Found memory routing for {count} agents")
    else:
        print("  ✗ Memory routing information not found in capabilities")

    print("\n" + "=" * 50)
    print("Test complete!")


if __name__ == "__main__":
    test_memory_routing()
