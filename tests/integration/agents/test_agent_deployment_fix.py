#!/usr/bin/env python3
"""
Test script to verify that agent deployment uses the correct user directory.

This script tests that:
1. AgentDeploymentService respects CLAUDE_MPM_USER_PWD environment variable
2. Agents are deployed to user directory, not framework directory
3. Project agents from user's .claude-mpm/agents/ are properly deployed
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logger import get_logger
from claude_mpm.services.agents.deployment import AgentDeploymentService

logger = get_logger("test_agent_deployment")


def test_deployment_with_user_directory():
    """Test that deployment service uses the correct user directory."""

    print("\n=== Testing Agent Deployment with User Directory ===\n")

    # Create a temporary directory to simulate user's project
    with tempfile.TemporaryDirectory() as temp_dir:
        user_dir = Path(temp_dir)
        print(f"✓ Created test user directory: {user_dir}")

        # Set the environment variable
        os.environ["CLAUDE_MPM_USER_PWD"] = str(user_dir)
        print(f"✓ Set CLAUDE_MPM_USER_PWD to: {user_dir}")

        # Test 1: AgentDeploymentService should use the user directory
        print("\n--- Test 1: Verify AgentDeploymentService uses user directory ---")
        deployment_service = AgentDeploymentService()

        # Check that working_directory is set correctly
        assert (
            deployment_service.working_directory == user_dir
        ), f"Expected working_directory to be {user_dir}, got {deployment_service.working_directory}"
        print(
            f"✓ AgentDeploymentService correctly using user directory: {deployment_service.working_directory}"
        )

        # Test 2: Deploy agents and verify they go to user directory
        print("\n--- Test 2: Deploy agents to user directory ---")
        results = deployment_service.deploy_agents()

        expected_target = user_dir / ".claude" / "agents"
        actual_target = Path(results["target_dir"])

        assert (
            actual_target == expected_target
        ), f"Expected agents to deploy to {expected_target}, got {actual_target}"
        print(f"✓ Agents deploying to correct location: {actual_target}")

        # Test 3: Verify agents were actually created
        if expected_target.exists():
            agent_files = list(expected_target.glob("*.md"))
            print(f"✓ Found {len(agent_files)} agent files in {expected_target}")
            for agent_file in agent_files[:3]:  # Show first 3
                print(f"  - {agent_file.name}")

        # Test 4: Test with explicit target directory
        print("\n--- Test 3: Deploy with explicit target directory ---")
        custom_target = user_dir / "custom" / ".claude"
        results = deployment_service.deploy_agents(target_dir=custom_target)

        expected_custom = custom_target / "agents"
        actual_custom = Path(results["target_dir"])

        assert (
            actual_custom == expected_custom
        ), f"Expected custom target {expected_custom}, got {actual_custom}"
        print(f"✓ Custom target deployment working: {actual_custom}")

        # Clean up environment variable
        del os.environ["CLAUDE_MPM_USER_PWD"]
        print("\n✓ All tests passed!")


def test_deployment_without_env_var():
    """Test that deployment falls back to current directory without env var."""

    print("\n=== Testing Agent Deployment Fallback (no env var) ===\n")

    # Make sure env var is not set
    if "CLAUDE_MPM_USER_PWD" in os.environ:
        del os.environ["CLAUDE_MPM_USER_PWD"]

    # Create deployment service
    deployment_service = AgentDeploymentService()

    # Should fall back to current directory
    assert (
        deployment_service.working_directory == Path.cwd()
    ), f"Expected working_directory to be {Path.cwd()}, got {deployment_service.working_directory}"
    print(
        f"✓ Without env var, correctly falls back to current directory: {deployment_service.working_directory}"
    )


def test_deployment_with_explicit_working_dir():
    """Test that explicit working_directory parameter takes precedence."""

    print("\n=== Testing Agent Deployment with Explicit Directory ===\n")

    with tempfile.TemporaryDirectory() as temp_dir:
        explicit_dir = Path(temp_dir)

        # Set env var to something different
        os.environ["CLAUDE_MPM_USER_PWD"] = "/some/other/path"

        # Create deployment service with explicit directory
        deployment_service = AgentDeploymentService(working_directory=explicit_dir)

        # Should use explicit directory, not env var
        assert (
            deployment_service.working_directory == explicit_dir
        ), f"Expected working_directory to be {explicit_dir}, got {deployment_service.working_directory}"
        print(
            f"✓ Explicit directory parameter takes precedence: {deployment_service.working_directory}"
        )

        # Clean up
        del os.environ["CLAUDE_MPM_USER_PWD"]


if __name__ == "__main__":
    try:
        test_deployment_with_user_directory()
        test_deployment_without_env_var()
        test_deployment_with_explicit_working_dir()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("=" * 50 + "\n")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
