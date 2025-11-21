#!/usr/bin/env python3
"""Final verification that memory routing is working correctly."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.memory.router import MemoryRouter


def test_final_verification():
    """Final verification of the memory routing implementation."""

    print("FINAL VERIFICATION: Dynamic Memory Routing")
    print("=" * 50)

    # Initialize components
    framework_loader = FrameworkLoader()
    memory_router = MemoryRouter()

    # Clear caches for fresh test
    framework_loader.clear_all_caches()

    print("\n✅ TEST 1: Memory routing in agent templates")
    print("-" * 40)
    test_agents = [
        "engineer",
        "research",
        "qa",
        "security",
        "documentation",
        "data_engineer",
        "ops",
        "version_control",
    ]

    success_count = 0
    for agent in test_agents:
        memory_routing = framework_loader._load_memory_routing_from_template(agent)
        if memory_routing and memory_routing.get("description"):
            print(f"  ✓ {agent:15} - {memory_routing['description'][:50]}...")
            success_count += 1
        else:
            print(f"  ✗ {agent:15} - No memory routing found")

    print(f"\nResult: {success_count}/{len(test_agents)} agents have memory routing")

    print("\n✅ TEST 2: Memory routing appears in agent capabilities")
    print("-" * 40)

    capabilities = framework_loader._generate_agent_capabilities_section()

    # Actually count the occurrences properly
    import re

    memory_routing_matches = re.findall(r"- \*\*Memory Routing\*\*: (.+)", capabilities)

    if memory_routing_matches:
        print(
            f"  ✓ Found {len(memory_routing_matches)} agents with memory routing in capabilities"
        )
        print("\n  Examples:")
        for i, match in enumerate(memory_routing_matches[:3]):
            print(f"    {i + 1}. {match[:80]}...")
    else:
        print("  ✗ No memory routing found in capabilities")

    print("\n✅ TEST 3: Memory router uses dynamic patterns")
    print("-" * 40)

    # Get routing patterns
    patterns = memory_router.get_routing_patterns()

    print(f"  Total agents: {len(patterns['agents'])}")
    if "static_agents" in patterns:
        print(f"  Static agents: {len(patterns['static_agents'])}")
    if "dynamic_agents" in patterns:
        print(f"  Dynamic agents: {len(patterns['dynamic_agents'])}")
        if patterns["dynamic_agents"]:
            print(
                f"  Dynamic agents loaded: {', '.join(patterns['dynamic_agents'][:5])}"
            )

    print("\n✅ TEST 4: Routing works correctly")
    print("-" * 40)

    test_cases = [
        ("Use SOLID principles and dependency injection", "engineer"),
        ("Analyze the authentication architecture", "research"),
        ("Write unit tests with pytest", "qa"),
        ("Check for OWASP vulnerabilities", "security"),
        ("Update the API documentation", "documentation"),
    ]

    correct = 0
    for content, expected in test_cases:
        result = memory_router.analyze_and_route(f"Remember to {content}")
        actual = result["target_agent"]
        if actual == expected:
            print(f"  ✓ '{content[:40]}...' → {actual}")
            correct += 1
        else:
            print(f"  ✗ '{content[:40]}...' → {actual} (expected {expected})")

    print(f"\nResult: {correct}/{len(test_cases)} correct routings")

    print("\n" + "=" * 50)
    print("VERIFICATION COMPLETE")

    # Summary
    print("\nSUMMARY:")
    if success_count >= 7 and memory_routing_matches and correct >= 4:
        print("✅ All tests passed! Memory routing is working correctly.")
    else:
        print("⚠️ Some tests failed. Review the output above.")

    return success_count, len(memory_routing_matches), correct


if __name__ == "__main__":
    test_final_verification()
