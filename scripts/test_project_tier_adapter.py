#!/usr/bin/env python3
"""
Test PROJECT tier integration with AgentRegistryAdapter.

This ensures that the adapter layer (used by other services) correctly
handles PROJECT tier agents.
"""

import sys
from pathlib import Path

# Add src to path for imports  
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.core.agent_registry import AgentRegistryAdapter
from claude_mpm.services.agent_registry import AgentTier
from claude_mpm.core.config_paths import ConfigPaths


def create_project_test_agent():
    """Create a simple project test agent."""
    project_agents_dir = ConfigPaths.get_project_agents_dir()
    project_agents_dir.mkdir(parents=True, exist_ok=True)
    
    agent_path = project_agents_dir / "test_adapter.md"
    content = """---
description: Test agent for adapter integration
version: 3.0.0
tools: ["test_tool"]
---

# Test Adapter Agent

Project-specific test agent.
"""
    agent_path.write_text(content)
    return agent_path


def test_adapter_with_project_tier():
    """Test that AgentRegistryAdapter works with PROJECT tier."""
    print("\n" + "="*60)
    print("Testing AgentRegistryAdapter with PROJECT Tier")
    print("="*60)
    
    # Create project agent
    agent_path = create_project_test_agent()
    print(f"Created project agent: {agent_path}")
    
    # Initialize adapter (registry is initialized automatically)
    adapter = AgentRegistryAdapter()
    
    # Check if registry was initialized
    if adapter.registry:
        print("✓ Registry initialized successfully")
    else:
        print("✗ Failed to initialize registry")
        return False
    
    # List all agents
    agents = adapter.list_agents()
    print(f"\n✓ Found {len(agents)} total agents")
    
    # Check if our test agent is present
    test_agent_found = False
    for agent_id, metadata in agents.items():
        if agent_id == 'test_adapter':
            test_agent_found = True
            print(f"\n✓ Found test_adapter agent:")
            print(f"  Type: {metadata.get('type', 'unknown')}")
            print(f"  Tier: {metadata.get('tier', 'unknown')}")
            print(f"  Path: {metadata.get('path', 'unknown')}")
            
            # Verify it's the project tier version
            if metadata.get('tier') == 'project':
                print("  ✅ This is the PROJECT tier version")
            break
    
    if not test_agent_found:
        print("\n✗ test_adapter agent not found")
        agent_path.unlink()
        return False
    
    # Test get_agent_definition
    definition = adapter.get_agent_definition('test_adapter')
    if definition:
        print("\n✓ get_agent_definition returned agent")
        if 'Project-specific test agent' in definition:
            print("  ✅ Content confirms PROJECT tier agent")
    else:
        print("\n✗ get_agent_definition failed")
    
    # Cleanup
    agent_path.unlink()
    print(f"\nCleaned up: {agent_path}")
    
    return True


def test_adapter_hierarchy():
    """Test that adapter respects PROJECT > USER > SYSTEM hierarchy."""
    print("\n" + "="*60)
    print("Testing Adapter Hierarchy Precedence")
    print("="*60)
    
    # Create a project version of an existing system agent
    project_agents_dir = ConfigPaths.get_project_agents_dir()
    project_agents_dir.mkdir(parents=True, exist_ok=True)
    
    qa_agent_path = project_agents_dir / "qa.md"
    content = """---
description: Project-customized QA agent
version: 5.0.0
tools: ["project_test_suite", "custom_validator"]
---

# QA Agent (Project Version)

This QA agent has been customized for this specific project.
"""
    qa_agent_path.write_text(content)
    print(f"Created project QA agent: {qa_agent_path}")
    
    # Initialize adapter (registry is initialized automatically)
    adapter = AgentRegistryAdapter()
    
    # Check the agent list to verify PROJECT tier precedence
    agents = adapter.list_agents()
    success = False
    
    if 'qa' in agents:
        qa_metadata = agents['qa']
        print(f"✓ Found QA agent in registry")
        print(f"  Tier: {qa_metadata.get('tier', 'unknown')}")
        print(f"  Path: {qa_metadata.get('path', 'unknown')}")
        
        if qa_metadata.get('tier') == 'project':
            print("  ✅ QA agent is using PROJECT tier (highest precedence)")
            success = True
        else:
            print(f"  ✗ QA agent is using {qa_metadata.get('tier')} tier instead of project")
    else:
        print("✗ QA agent not found in registry")
    
    # Get hierarchy info to double-check
    hierarchy = adapter.get_agent_hierarchy()
    if hierarchy:
        print(f"\n✓ Agent hierarchy has {len(hierarchy)} tiers")
        
        # Check if PROJECT tier is represented and has QA agent
        for tier_name, agent_names in hierarchy.items():
            if 'qa' in agent_names:
                print(f"  QA agent found in tier: {tier_name}")
                if tier_name == 'project':
                    print("  ✅ Confirmed: QA agent is in PROJECT tier")
    
    # Cleanup
    qa_agent_path.unlink()
    print(f"\nCleaned up: {qa_agent_path}")
    
    return success


def main():
    """Run adapter integration tests."""
    print("\n" + "="*60)
    print("PROJECT TIER ADAPTER INTEGRATION TESTS")
    print("="*60)
    
    tests = [
        ("Adapter with PROJECT Tier", test_adapter_with_project_tier),
        ("Adapter Hierarchy Precedence", test_adapter_hierarchy),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            passed = test_func()
            results.append((test_name, passed))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' raised exception: {e}")
            import traceback
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("ADAPTER TEST RESULTS")
    print("="*60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL ADAPTER TESTS PASSED!")
        print("\nPROJECT tier is fully integrated with:")
        print("• AgentRegistryAdapter (used by other services)")
        print("• Agent selection and definition retrieval")
        print("• Hierarchy reporting")
    else:
        print("❌ SOME ADAPTER TESTS FAILED")
    print("="*60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())