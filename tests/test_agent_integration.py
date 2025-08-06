#!/usr/bin/env python3
"""Test claude-mpm agent registry integration."""

import sys
from pathlib import Path

# Add parent directory to path for development
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from core.agent_registry import AgentRegistryAdapter
from orchestration.agent_delegator import AgentDelegator
from core.framework_loader import FrameworkLoader


def test_agent_registry():
    """Test agent registry functionality."""
    print("=== Agent Registry Test ===\n")
    
    # Create registry adapter
    adapter = AgentRegistryAdapter()
    
    if adapter.framework_path:
        print(f"✅ Found framework at: {adapter.framework_path}")
    else:
        print("⚠️  Framework not found - using minimal functionality")
        return False
    
    if adapter.registry:
        print("✅ Agent registry initialized")
        
        # List agents
        agents = adapter.list_agents()
        print(f"\nFound {len(agents)} agents:")
        for agent_id, metadata in list(agents.items())[:5]:  # Show first 5
            print(f"  - {agent_id}: {metadata.get('type', 'unknown')}")
        
        # Get hierarchy
        hierarchy = adapter.get_agent_hierarchy()
        print(f"\nAgent Hierarchy:")
        print(f"  Project agents: {len(hierarchy['project'])}")
        print(f"  User agents: {len(hierarchy['user'])}")
        print(f"  System agents: {len(hierarchy['system'])}")
        
        # Get core agents
        core_agents = adapter.get_core_agents()
        print(f"\nCore agents: {', '.join(core_agents)}")
        
    else:
        print("⚠️  Agent registry not available")
    
    return True


def test_agent_delegator():
    """Test agent delegation detection."""
    print("\n=== Agent Delegator Test ===\n")
    
    # Create delegator with registry
    adapter = AgentRegistryAdapter()
    delegator = AgentDelegator(agent_registry=adapter)
    
    # Test delegation patterns
    test_cases = [
        "Delegate to Engineer: Implement the user authentication system",
        "→ QA Agent: Write comprehensive test coverage",
        "Task for Documentation: Update the API docs with new endpoints",
        "Research Agent should: Investigate caching strategies",
        "Ask Ops to: Set up monitoring and alerting",
    ]
    
    print("Testing delegation patterns:")
    for text in test_cases:
        delegations = delegator.extract_delegations(text)
        if delegations:
            d = delegations[0]
            print(f"  ✓ {d['pattern_type']}: {d['agent']} → {d['task'][:50]}...")
    
    # Test agent suggestions
    print("\nTesting agent suggestions:")
    tasks = [
        "Write unit tests for the new feature",
        "Deploy the application to staging",
        "Update the changelog with recent commits",
        "Investigate memory leak issues",
        "Set up database backups",
    ]
    
    for task in tasks:
        suggested = delegator.suggest_agent_for_task(task)
        print(f"  - '{task[:40]}...' → {suggested}")
    
    # Test Task Tool formatting
    print("\nTask Tool Format Example:")
    formatted = delegator.format_task_tool_delegation(
        "engineer",
        "Implement JWT authentication",
        "Use industry best practices and include refresh tokens"
    )
    print(formatted)
    
    return True


def test_framework_loader_integration():
    """Test framework loader with agent registry."""
    print("\n=== Framework Loader Integration Test ===\n")
    
    loader = FrameworkLoader()
    
    print(f"Framework loaded: {loader.framework_content['loaded']}")
    if loader.framework_content['loaded']:
        print(f"Framework version: {loader.framework_content['version']}")
    
    # Test agent list (should use registry if available)
    agents = loader.get_agent_list()
    print(f"\nAvailable agents: {len(agents)}")
    if agents:
        print(f"Sample agents: {', '.join(list(agents)[:10])}")
    
    # Test agent definition retrieval
    if agents and 'engineer' in agents:
        definition = loader.get_agent_definition('engineer')
        if definition:
            print(f"\nEngineer agent definition found ({len(definition)} chars)")
            print("First 200 chars:")
            print(definition[:200] + "...")
    
    # Test hierarchy
    if loader.agent_registry:
        hierarchy = loader.get_agent_hierarchy()
        print(f"\nAgent hierarchy from loader:")
        for level, agents in hierarchy.items():
            print(f"  {level}: {len(agents)} agents")
    
    return True


def main():
    """Run all integration tests."""
    print("Claude MPM - Agent Integration Tests")
    print("=" * 50)
    
    tests = [
        ("Agent Registry", test_agent_registry),
        ("Agent Delegator", test_agent_delegator),
        ("Framework Loader Integration", test_framework_loader_integration),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"\n{'='*50}")
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"\n❌ {test_name} failed with error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print(f"\n{'='*50}")
    print(f"Integration tests completed: {passed} passed, {failed} failed")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())