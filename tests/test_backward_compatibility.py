#\!/usr/bin/env python3
"""Test backward compatibility of agent service imports."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def test_old_imports():
    """Test that old import paths still work."""
    print("Testing backward compatibility imports...")
    
    # Test main services imports
    try:
        from claude_mpm.services import (
            AgentDeploymentService,
            AgentRegistry,
            AgentMemoryManager,
            AgentLifecycleManager,
            AgentManager,
            AgentCapabilitiesGenerator,
        )
        print("✓ All main service imports work from claude_mpm.services")
    except ImportError as e:
        print(f"✗ Failed to import from claude_mpm.services: {e}")
        return False
    
    # Test that they're the same as the new imports
    try:
        from claude_mpm.services.agents.deployment import AgentDeploymentService as NewDeployment
        from claude_mpm.services.agents.registry import AgentRegistry as NewRegistry
        from claude_mpm.services.agents.memory import AgentMemoryManager as NewMemory
        
        assert AgentDeploymentService is NewDeployment
        assert AgentRegistry is NewRegistry
        assert AgentMemoryManager is NewMemory
        print("✓ Old imports reference the same classes as new imports")
    except (ImportError, AssertionError) as e:
        print(f"✗ Import mismatch: {e}")
        return False
    
    return True

def test_new_imports():
    """Test that new hierarchical imports work."""
    print("\nTesting new hierarchical imports...")
    
    try:
        from claude_mpm.services.agents.registry import (
            AgentRegistry,
            AgentMetadata,
            AgentTier,
            AgentType,
        )
        from claude_mpm.services.agents.deployment import (
            AgentDeploymentService,
            AgentLifecycleManager,
            LifecycleState,
        )
        from claude_mpm.services.agents.memory import (
            AgentMemoryManager,
            get_memory_manager,
            AgentPersistenceService,
        )
        from claude_mpm.services.agents.management import (
            AgentManager,
            AgentCapabilitiesGenerator,
        )
        from claude_mpm.services.agents.loading import (
            FrameworkAgentLoader,
            AgentProfileLoader,
            BaseAgentManager,
        )
        print("✓ All new hierarchical imports work")
        return True
    except ImportError as e:
        print(f"✗ Failed new imports: {e}")
        return False

def test_functionality():
    """Test that imported classes actually work."""
    print("\nTesting functionality...")
    
    try:
        from claude_mpm.services import AgentRegistry
        
        # Create an instance
        registry = AgentRegistry()
        
        # Call a method
        agents = registry.discover_agents()
        
        print(f"✓ AgentRegistry works, discovered {len(agents)} agents")
        return True
    except Exception as e:
        print(f"✗ Functionality test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("=" * 60)
    print("AGENT SERVICE REORGANIZATION BACKWARD COMPATIBILITY TEST")
    print("=" * 60)
    
    results = []
    
    results.append(("Old imports", test_old_imports()))
    results.append(("New imports", test_new_imports()))
    results.append(("Functionality", test_functionality()))
    
    print("\n" + "=" * 60)
    print("RESULTS:")
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n✅ All backward compatibility tests passed!")
        print("The hierarchical reorganization maintains full backward compatibility.")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())