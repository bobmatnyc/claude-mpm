#!/usr/bin/env python3
"""
Verification script for import fixes in claude-mpm.

WHY: This script verifies that all the import statements that were updated to use
the backward compatibility layer work correctly. It tests the imports in isolation
and ensures the services can be instantiated without errors.

DESIGN DECISION: We test each import in a separate try-except block to identify
exactly which imports might still have issues, rather than having one failure
prevent testing of other imports.
"""

import sys
import traceback
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_import(module_path: str, import_statement: str, test_name: str) -> bool:
    """
    Test a specific import statement.

    Args:
        module_path: Module path to test
        import_statement: Import statement to execute
        test_name: Name of the test for reporting

    Returns:
        True if import succeeded, False otherwise
    """
    print(f"\nTesting {test_name}...")
    print(f"  Module: {module_path}")
    print(f"  Import: {import_statement}")

    try:
        # Create a namespace for the exec
        namespace = {}

        # Execute the import in the namespace
        exec(import_statement, namespace)
        print(f"  ✓ Import successful")

        # Try to instantiate if it's a service
        if "AgentDeploymentService" in import_statement:
            # Get the imported class from namespace
            AgentDeploymentService = namespace.get("AgentDeploymentService")
            if AgentDeploymentService:
                service = AgentDeploymentService()
                print(f"  ✓ Service instantiation successful")
            else:
                print(f"  ✗ AgentDeploymentService not found in namespace")
                return False
        elif "AgentManager" in import_statement:
            # Get the imported class from namespace
            AgentManager = namespace.get("AgentManager")
            if AgentManager:
                manager = AgentManager()
                print(f"  ✓ Manager instantiation successful")
            else:
                print(f"  ✗ AgentManager not found in namespace")
                return False

        return True
    except Exception as e:
        print(f"  ✗ Failed: {e}")
        if "--verbose" in sys.argv:
            traceback.print_exc()
        return False


def main():
    """Main verification function."""
    print("=" * 80)
    print("Verifying Import Fixes for Claude-MPM")
    print("=" * 80)

    tests = [
        # Test 1: core/factories.py
        {
            "name": "core/factories.py",
            "module": "claude_mpm.core.factories",
            "import": "from claude_mpm.services import AgentDeploymentService",
        },
        # Test 2: core/service_registry.py
        {
            "name": "core/service_registry.py",
            "module": "claude_mpm.core.service_registry",
            "import": "from claude_mpm.services import AgentDeploymentService",
        },
        # Test 3: cli/utils.py
        {
            "name": "cli/utils.py",
            "module": "claude_mpm.cli.utils",
            "import": "from claude_mpm.services import AgentDeploymentService",
        },
        # Test 4: cli/commands/agents.py
        {
            "name": "cli/commands/agents.py",
            "module": "claude_mpm.cli.commands.agents",
            "import": "from claude_mpm.services import AgentDeploymentService",
        },
        # Test 5: agents/agent_loader_integration.py
        {
            "name": "agents/agent_loader_integration.py",
            "module": "claude_mpm.agents.agent_loader_integration",
            "import": "from claude_mpm.services import AgentManager",
        },
    ]

    # Run all tests
    results = []
    for test in tests:
        success = test_import(test["module"], test["import"], test["name"])
        results.append((test["name"], success))

    # Print summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    failed = len(results) - passed

    for name, success in results:
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"  {name:<40} {status}")

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")

    # Now test that the actual modules can be imported and used
    print("\n" + "=" * 80)
    print("INTEGRATION TEST: Loading Actual Modules")
    print("=" * 80)

    integration_tests_passed = True

    # Test 1: Import and use factories
    try:
        print("\n1. Testing core/factories.py module...")
        from claude_mpm.core.factories import AgentServiceFactory

        print("   ✓ Module imported successfully")
        factory = AgentServiceFactory()
        print("   ✓ Factory instantiated successfully")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        integration_tests_passed = False

    # Test 2: Import and use service_registry
    try:
        print("\n2. Testing core/service_registry.py module...")
        from claude_mpm.core.service_registry import ServiceRegistry

        print("   ✓ Module imported successfully")
        # Don't instantiate as it requires container setup
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        integration_tests_passed = False

    # Test 3: Import and use cli/utils
    try:
        print("\n3. Testing cli/utils.py module...")
        from claude_mpm.cli.utils import get_agent_versions_display

        print("   ✓ Module imported successfully")
        # Function exists and can be called (might return None if no agents deployed)
        result = get_agent_versions_display()
        print(f"   ✓ Function callable (returned: {'data' if result else 'None'})")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        integration_tests_passed = False

    # Test 4: Import and use cli/commands/agents
    try:
        print("\n4. Testing cli/commands/agents.py module...")
        from claude_mpm.cli.commands.agents import manage_agents

        print("   ✓ Module imported successfully")
        print("   ✓ Function 'manage_agents' exists")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        integration_tests_passed = False

    # Test 5: Import and use agent_loader_integration
    try:
        print("\n5. Testing agents/agent_loader_integration.py module...")
        from claude_mpm.agents.agent_loader_integration import EnhancedAgentLoader

        print("   ✓ Module imported successfully")
        loader = EnhancedAgentLoader()
        print("   ✓ EnhancedAgentLoader instantiated successfully")
    except Exception as e:
        print(f"   ✗ Failed: {e}")
        integration_tests_passed = False

    # Final verdict
    print("\n" + "=" * 80)
    print("FINAL VERDICT")
    print("=" * 80)

    if passed == len(results) and integration_tests_passed:
        print("✅ All import fixes verified successfully!")
        print("The backward compatibility layer is working correctly.")
        return 0
    else:
        print("❌ Some imports still have issues.")
        print("Please review the failed tests above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
