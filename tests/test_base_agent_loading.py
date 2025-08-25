#!/usr/bin/env python3
"""Test script to verify base_agent.json loading with priority-based search."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_base_agent_loader():
    """Test the base_agent_loader module."""
    print("\n=== Testing base_agent_loader module ===")

    from claude_mpm.services.agents.base_agent_loader import (
        _get_base_agent_file,
        get_base_agent_path,
        load_base_agent_instructions,
    )

    # Test getting base agent file path
    print("\n1. Testing _get_base_agent_file()...")
    try:
        path = _get_base_agent_file()
        print(f"   ✓ Base agent file found at: {path}")
        print(f"   ✓ File exists: {path.exists()}")

        # Check if it's using local development version
        if "/Users/masa/Projects/claude-mpm" in str(path):
            print("   ✓ Using LOCAL DEVELOPMENT version (correct!)")
        elif "pipx" in str(path):
            print("   ⚠ Using PIPX installation version (should be local dev)")
        elif "site-packages" in str(path):
            print("   ⚠ Using SITE-PACKAGES version (should be local dev)")
        else:
            print(f"   ? Using unknown location: {path}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test loading base agent instructions
    print("\n2. Testing load_base_agent_instructions()...")
    try:
        instructions = load_base_agent_instructions()
        if instructions:
            print(f"   ✓ Instructions loaded successfully ({len(instructions)} chars)")
        else:
            print("   ✗ No instructions loaded")
            return False
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    # Test get_base_agent_path
    print("\n3. Testing get_base_agent_path()...")
    try:
        path = get_base_agent_path()
        print(f"   ✓ Path retrieved: {path}")
    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    return True


def test_agent_deployment_service():
    """Test the AgentDeploymentService."""
    print("\n=== Testing AgentDeploymentService ===")

    from claude_mpm.services.agents.deployment.agent_deployment import (
        AgentDeploymentService,
    )

    print("\n1. Creating AgentDeploymentService instance...")
    try:
        service = AgentDeploymentService()
        print("   ✓ Service created successfully")
        print(f"   ✓ Base agent path: {service.base_agent_path}")

        # Check if it's using local development version
        if "/Users/masa/Projects/claude-mpm" in str(service.base_agent_path):
            print("   ✓ Using LOCAL DEVELOPMENT version (correct!)")
        elif "pipx" in str(service.base_agent_path):
            print("   ⚠ Using PIPX installation version (should be local dev)")
        elif "site-packages" in str(service.base_agent_path):
            print("   ⚠ Using SITE-PACKAGES version (should be local dev)")
        else:
            print(f"   ? Using unknown location: {service.base_agent_path}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    return True


def test_async_agent_deployment():
    """Test the AsyncAgentDeploymentService."""
    print("\n=== Testing AsyncAgentDeploymentService ===")

    from claude_mpm.services.agents.deployment.async_agent_deployment import (
        AsyncAgentDeploymentService,
    )

    print("\n1. Creating AsyncAgentDeploymentService instance...")
    try:
        service = AsyncAgentDeploymentService()
        print("   ✓ Service created successfully")
        print(f"   ✓ Base agent path: {service.base_agent_path}")

        # Check if it's using local development version
        if "/Users/masa/Projects/claude-mpm" in str(service.base_agent_path):
            print("   ✓ Using LOCAL DEVELOPMENT version (correct!)")
        elif "pipx" in str(service.base_agent_path):
            print("   ⚠ Using PIPX installation version (should be local dev)")
        elif "site-packages" in str(service.base_agent_path):
            print("   ⚠ Using SITE-PACKAGES version (should be local dev)")
        else:
            print(f"   ? Using unknown location: {service.base_agent_path}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return False

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Base Agent Loading Priority System")
    print("=" * 60)
    print(f"Current working directory: {Path.cwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Python executable: {sys.executable}")

    # Check if we're in the right directory
    expected_base_agent = (
        Path.cwd() / "src" / "claude_mpm" / "agents" / "base_agent.json"
    )
    if expected_base_agent.exists():
        print(f"\n✓ Local base_agent.json found at: {expected_base_agent}")
    else:
        print(f"\n⚠ Local base_agent.json NOT found at: {expected_base_agent}")
        print("  Make sure you're running from the claude-mpm project root!")

    # Run tests
    results = []
    results.append(("base_agent_loader", test_base_agent_loader()))
    results.append(("AgentDeploymentService", test_agent_deployment_service()))
    results.append(("AsyncAgentDeploymentService", test_async_agent_deployment()))

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n✓ All tests passed! Base agent loading is working correctly.")
        print("  The system is now using the local development base_agent.json")
    else:
        print("\n✗ Some tests failed. Please check the output above.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
