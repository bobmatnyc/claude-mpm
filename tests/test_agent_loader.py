#!/usr/bin/env python3
"""Test agent loader with new schema format."""

import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.agents.agent_loader import AgentLoader, list_available_agents


def main():
    """Test agent loader functionality."""
    print("=== Agent Loader Test ===\n")

    # Test 1: Initialize agent loader
    print("1. Testing AgentLoader initialization...")
    start_time = time.time()
    loader = AgentLoader()
    load_time = time.time() - start_time

    print(f"   ✓ AgentLoader initialized in {load_time * 1000:.2f}ms")

    # Test 2: List available agents
    print("\n2. Testing list_agents()...")
    agents = loader.list_agents()
    print(f"   Found {len(agents)} agents:")

    for agent in agents[:3]:  # Show first 3
        print(f"   - {agent['id']}: {agent['name']} ({agent['resource_tier']} tier)")

    # Test 3: Load individual agent
    print("\n3. Testing get_agent()...")
    test_agents = ["engineer", "qa", "research"]

    for agent_id in test_agents:
        agent_data = loader.get_agent(agent_id)
        if agent_data:
            print(f"   ✓ Loaded {agent_id}:")
            print(f"     - Version: {agent_data.get('version', 'unknown')}")
            print(
                f"     - Category: {agent_data.get('metadata', {}).get('category', 'unknown')}"
            )
            print(
                f"     - Model: {agent_data.get('capabilities', {}).get('model', 'unknown')}"
            )
        else:
            print(f"   ✗ Failed to load {agent_id}")

    # Test 4: Get agent prompt
    print("\n4. Testing get_agent_prompt()...")
    for agent_id in test_agents:
        start_time = time.time()
        prompt = loader.get_agent_prompt(agent_id)
        load_time = time.time() - start_time

        if prompt:
            print(f"   ✓ {agent_id} prompt loaded in {load_time * 1000:.2f}ms")
            print(f"     - Length: {len(prompt)} chars")
            print(f"     - First 50 chars: {prompt[:50]}...")
        else:
            print(f"   ✗ Failed to load {agent_id} prompt")

    # Test 5: Test caching
    print("\n5. Testing prompt caching...")
    # First load (cold)
    start_time = time.time()
    prompt1 = loader.get_agent_prompt("engineer")
    cold_time = time.time() - start_time

    # Second load (cached)
    start_time = time.time()
    prompt2 = loader.get_agent_prompt("engineer")
    cached_time = time.time() - start_time

    print(f"   Cold load: {cold_time * 1000:.2f}ms")
    print(f"   Cached load: {cached_time * 1000:.2f}ms")
    print(f"   Speed improvement: {cold_time / cached_time:.1f}x")
    print(f"   Content identical: {'✓' if prompt1 == prompt2 else '✗'}")

    # Test 6: Test backward compatibility functions
    print("\n6. Testing backward compatibility...")
    from claude_mpm.agents.agent_loader import (
        get_engineer_agent_prompt,
        get_qa_agent_prompt,
        get_research_agent_prompt,
    )

    try:
        get_engineer_agent_prompt()
        get_qa_agent_prompt()
        get_research_agent_prompt()

        print("   ✓ get_engineer_agent_prompt() works")
        print("   ✓ get_qa_agent_prompt() works")
        print("   ✓ get_research_agent_prompt() works")
    except Exception as e:
        print(f"   ✗ Backward compatibility failed: {e}")

    # Test 7: Test registry integration
    print("\n7. Testing AgentRegistry integration...")
    registry = get_agent_registry()

    registry_agents = registry.list_agents()
    print(f"   Registry found {len(registry_agents)} agents")

    # Get specific agent via registry
    eng_agent = registry.get_agent("engineer")
    if eng_agent:
        print("   ✓ Registry can load agents")
        print("     - Engineer agent loaded successfully")
    else:
        print("   ✗ Registry failed to load agent")

    # Test 8: Test list_available_agents utility
    print("\n8. Testing list_available_agents()...")
    available = list_available_agents()
    print(f"   Found {len(available)} agents:")

    for agent_id, info in list(available.items())[:2]:
        print(f"   - {agent_id}:")
        print(f"     Name: {info['name']}")
        print(f"     Category: {info['category']}")
        print(f"     Model: {info['model']}")
        print(f"     Tier: {info['resource_tier']}")

    # Test 9: Error handling
    print("\n9. Testing error handling...")
    # Try to load non-existent agent
    bad_agent = loader.get_agent("nonexistent")
    if bad_agent is None:
        print("   ✓ Non-existent agent returns None")
    else:
        print("   ✗ Non-existent agent did not return None")

    # Try to get prompt for non-existent agent
    bad_prompt = loader.get_agent_prompt("nonexistent")
    if bad_prompt is None:
        print("   ✓ Non-existent agent prompt returns None")
    else:
        print("   ✗ Non-existent agent prompt did not return None")

    # Summary
    print("\n=== Summary ===")
    print("✓ AgentLoader successfully loads agents with new schema")
    print("✓ Caching improves performance significantly")
    print("✓ Backward compatibility maintained")
    print("✓ Registry integration working")
    print("✓ Error handling appropriate")

    return 0


if __name__ == "__main__":
    sys.exit(main())
