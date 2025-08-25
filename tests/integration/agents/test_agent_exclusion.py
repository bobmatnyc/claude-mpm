#!/usr/bin/env python3
"""
Test script for agent exclusion functionality.

This script demonstrates how to configure and test agent exclusions
during deployment.
"""

import shutil
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logger import get_logger
from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)


def test_agent_exclusion():
    """Test agent exclusion functionality."""
    logger = get_logger("test_exclusion")

    print("=" * 80)
    print("AGENT EXCLUSION TEST")
    print("=" * 80)

    # Create a temporary deployment directory
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)
        target_dir = temp_path / ".claude" / "agents"

        print(f"\n1. Setting up test deployment to: {target_dir}")

        # Test 1: Deploy without exclusions
        print("\n2. Testing deployment WITHOUT exclusions...")
        print("-" * 40)

        config = Config()
        config.set("agent_deployment.excluded_agents", [])

        service = AgentDeploymentService()
        results = service.deploy_agents(
            target_dir=target_dir, force_rebuild=True, config=config
        )

        print(f"   Deployed: {len(results['deployed'])} agents")
        print(f"   Updated: {len(results['updated'])} agents")
        print(f"   Errors: {len(results['errors'])} agents")

        initial_count = len(results["deployed"]) + len(results["updated"])
        print(f"   Total agents deployed: {initial_count}")

        # Clean up for next test
        shutil.rmtree(target_dir, ignore_errors=True)

        # Test 2: Deploy with exclusions
        print("\n3. Testing deployment WITH exclusions...")
        print("-" * 40)

        # Configure exclusions
        excluded_agents = ["research", "data_engineer", "version_control"]
        config.set("agent_deployment.excluded_agents", excluded_agents)
        config.set("agent_deployment.case_sensitive", False)

        print(f"   Excluding agents: {', '.join(excluded_agents)}")
        print("   Case sensitive: False")

        results = service.deploy_agents(
            target_dir=target_dir, force_rebuild=True, config=config
        )

        print(f"   Deployed: {len(results['deployed'])} agents")
        print(f"   Updated: {len(results['updated'])} agents")
        print(f"   Errors: {len(results['errors'])} agents")

        excluded_count = len(results["deployed"]) + len(results["updated"])
        print(f"   Total agents deployed: {excluded_count}")

        # Verify exclusions worked
        expected_excluded = len(excluded_agents)
        actual_excluded = initial_count - excluded_count

        print("\n4. Verification:")
        print("-" * 40)
        print(f"   Expected to exclude: {expected_excluded} agents")
        print(f"   Actually excluded: {actual_excluded} agents")

        # List deployed agents
        deployed_agents = [agent["name"] for agent in results["deployed"]]
        print(f"   Deployed agents: {', '.join(sorted(deployed_agents))}")

        # Check that excluded agents are not in deployed list
        excluded_found = []
        for excluded in excluded_agents:
            if excluded.lower() in [a.lower() for a in deployed_agents]:
                excluded_found.append(excluded)

        if excluded_found:
            print(
                f"   ❌ ERROR: Excluded agents were deployed: {', '.join(excluded_found)}"
            )
        else:
            print("   ✅ SUCCESS: All excluded agents were properly filtered")

        # Test 3: Case sensitivity test
        print("\n5. Testing case sensitivity...")
        print("-" * 40)

        # Clean up
        shutil.rmtree(target_dir, ignore_errors=True)

        # Test with case-sensitive matching
        config.set(
            "agent_deployment.excluded_agents", ["Research", "Data_Engineer"]
        )  # Wrong case
        config.set("agent_deployment.case_sensitive", True)

        print("   Excluding agents: Research, Data_Engineer (wrong case)")
        print("   Case sensitive: True")

        results = service.deploy_agents(
            target_dir=target_dir, force_rebuild=True, config=config
        )

        case_sensitive_count = len(results["deployed"]) + len(results["updated"])

        # These should NOT be excluded because case doesn't match
        deployed_agents = [agent["name"] for agent in results["deployed"]]
        if "research" in deployed_agents and "data_engineer" in deployed_agents:
            print(
                "   ✅ Case-sensitive matching works: agents not excluded with wrong case"
            )
        else:
            print("   ❌ Case-sensitive matching failed")

        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)


def test_configuration_file():
    """Test loading exclusions from configuration file."""
    print("\n" + "=" * 80)
    print("CONFIGURATION FILE TEST")
    print("=" * 80)

    # Create a temporary configuration file
    with tmp_path as temp_dir:
        temp_path = Path(temp_dir)
        config_dir = temp_path / ".claude-mpm"
        config_dir.mkdir()

        config_file = config_dir / "configuration.yaml"

        # Write test configuration
        config_content = """
agent_deployment:
  excluded_agents:
    - research
    - data_engineer
    - ops
  case_sensitive: false
  exclude_dependencies: false
"""
        config_file.write_text(config_content)

        print(f"\n1. Created configuration file at: {config_file}")
        print("   Configuration content:")
        for line in config_content.strip().split("\n"):
            print(f"     {line}")

        # Change to temp directory to test configuration loading
        import os

        original_cwd = os.getcwd()
        os.chdir(temp_path)

        try:
            # Load configuration
            config = Config()

            excluded = config.get("agent_deployment.excluded_agents", [])
            case_sensitive = config.get("agent_deployment.case_sensitive", False)

            print("\n2. Loaded configuration:")
            print(f"   Excluded agents: {excluded}")
            print(f"   Case sensitive: {case_sensitive}")

            if excluded == ["research", "data_engineer", "ops"]:
                print("   ✅ Configuration loaded correctly")
            else:
                print("   ❌ Configuration loading failed")

        finally:
            os.chdir(original_cwd)

    print("\n" + "=" * 80)
    print("CONFIGURATION FILE TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    # Test exclusion functionality
    test_agent_exclusion()

    # Test configuration file loading
    test_configuration_file()

    print("\n✅ All tests completed!")
