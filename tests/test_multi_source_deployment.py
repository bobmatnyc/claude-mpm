#!/usr/bin/env python3
"""Test script for multi-source agent deployment with version comparison.

This script tests that the highest version agent is deployed regardless of source.
"""

import json
import sys
import tempfile
from pathlib import Path

# Add the src directory to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment.agent_deployment import (
    AgentDeploymentService,
)
from claude_mpm.services.agents.deployment.multi_source_deployment_service import (
    MultiSourceAgentDeploymentService,
)


def create_test_agent(name: str, version: str, source: str) -> dict:
    """Create a test agent configuration."""
    return {
        "schema_version": "1.2.0",
        "agent_id": f"{name}-agent",
        "agent_version": version,
        "agent_type": name,
        "metadata": {
            "name": f"{name.title()} Agent",
            "description": f"Test {name} agent from {source}",
            "category": "test",
            "tags": ["test"],
            "author": "Test",
        },
        "capabilities": {
            "model": "sonnet",
            "tools": ["Read", "Write"],
        },
        "instructions": f"# {name.title()} Agent\n\nFrom {source} with version {version}",
    }


def setup_test_directories():
    """Set up test directories with different agent versions."""
    # Create temporary directories
    temp_base = Path(tempfile.mkdtemp(prefix="claude_mpm_test_"))

    system_dir = temp_base / "system" / "templates"
    project_dir = temp_base / "project" / ".claude-mpm" / "agents"
    user_dir = temp_base / "user" / ".claude-mpm" / "agents"

    system_dir.mkdir(parents=True)
    project_dir.mkdir(parents=True)
    user_dir.mkdir(parents=True)

    # Create test agents with different versions
    test_cases = [
        # qa agent: system has highest version
        ("qa", "3.2.0", system_dir, "system"),
        ("qa", "2.5.0", project_dir, "project"),
        ("qa", "1.0.0", user_dir, "user"),
        # engineer agent: project has highest version
        ("engineer", "2.0.0", system_dir, "system"),
        ("engineer", "4.1.0", project_dir, "project"),
        ("engineer", "3.0.0", user_dir, "user"),
        # security agent: user has highest version
        ("security", "1.5.0", system_dir, "system"),
        ("security", "2.0.0", project_dir, "project"),
        ("security", "5.0.0", user_dir, "user"),
        # ops agent: only in system
        ("ops", "1.2.0", system_dir, "system"),
        # custom agent: only in project
        ("custom", "1.0.0", project_dir, "project"),
    ]

    for agent_name, version, directory, source in test_cases:
        agent_file = directory / f"{agent_name}.json"
        agent_data = create_test_agent(agent_name, version, source)
        agent_file.write_text(json.dumps(agent_data, indent=2))

    # Also create base_agent.json in system dir
    base_agent = {
        "base_version": "1.0.0",
        "content": "# Base Agent\n\nBase agent content",
    }
    (system_dir.parent / "base_agent.json").write_text(json.dumps(base_agent, indent=2))

    return temp_base, system_dir, project_dir.parent.parent, user_dir.parent.parent


def test_multi_source_discovery():
    """Test that agents are discovered from all sources."""
    print("\n=== Testing Multi-Source Agent Discovery ===\n")

    temp_base, system_dir, project_base, user_base = setup_test_directories()

    try:
        service = MultiSourceAgentDeploymentService()

        # Discover agents from all sources
        agents_by_name = service.discover_agents_from_all_sources(
            system_templates_dir=system_dir,
            project_agents_dir=project_base / ".claude-mpm" / "agents",
            user_agents_dir=user_base / ".claude-mpm" / "agents",
        )

        print("Discovered agents from multiple sources:")
        for agent_name, versions in agents_by_name.items():
            print(f"\n  {agent_name}:")
            for version_info in versions:
                print(f"    - {version_info['source']}: v{version_info['version']}")

        # Select highest versions
        selected = service.select_highest_version_agents(agents_by_name)

        print("\n\nSelected highest versions:")
        for agent_name, agent_info in selected.items():
            print(
                f"  {agent_name}: v{agent_info['version']} from {agent_info['source']}"
            )

        # Verify expected results (use actual agent names from discovery)
        expected = {
            "Qa Agent": ("3.2.0", "system"),
            "Engineer Agent": ("4.1.0", "project"),
            "Security Agent": ("5.0.0", "user"),
            "Ops Agent": ("1.2.0", "system"),
            "Custom Agent": ("1.0.0", "project"),
        }

        print("\n\nVerifying results:")
        all_correct = True
        for agent_name, (expected_version, expected_source) in expected.items():
            if agent_name in selected:
                actual_version = selected[agent_name]["version"]
                actual_source = selected[agent_name]["source"]
                if (
                    actual_version == expected_version
                    and actual_source == expected_source
                ):
                    print(
                        f"  ✓ {agent_name}: Correct (v{expected_version} from {expected_source})"
                    )
                else:
                    print(
                        f"  ✗ {agent_name}: Expected v{expected_version} from {expected_source}, "
                        f"got v{actual_version} from {actual_source}"
                    )
                    all_correct = False
            else:
                print(f"  ✗ {agent_name}: Not found in selected agents")
                all_correct = False

        if all_correct:
            print("\n✅ All tests passed! Highest versions correctly selected.")
        else:
            print("\n❌ Some tests failed. Check the results above.")

        return all_correct

    finally:
        # Clean up
        import shutil

        shutil.rmtree(temp_base, ignore_errors=True)


def test_deployment_integration():
    """Test that the main deployment service uses multi-source correctly."""
    print("\n=== Testing Deployment Service Integration ===\n")

    temp_base, system_dir, project_base, _user_base = setup_test_directories()

    try:
        # Create deployment target directory
        target_dir = temp_base / "deployed" / ".claude" / "agents"
        target_dir.mkdir(parents=True)

        # Test with update mode (should use multi-source)
        print("Testing with 'update' mode (should use multi-source):")
        service = AgentDeploymentService(
            templates_dir=system_dir,
            working_directory=project_base,
        )

        results = service.deploy_agents(
            target_dir=target_dir.parent,
            deployment_mode="update",
            force_rebuild=True,
        )

        if results.get("multi_source"):
            print("  ✓ Multi-source deployment was used")

            # Check agent sources
            if results.get("agent_sources"):
                print("\n  Agent sources:")
                for agent, source in results["agent_sources"].items():
                    print(f"    {agent}: {source}")
        else:
            print("  ✗ Multi-source deployment was NOT used (expected it to be used)")

        # Check deployed agents
        deployed_files = list(target_dir.glob("*.md"))
        print(f"\n  Deployed {len(deployed_files)} agents:")

        for agent_file in deployed_files:
            content = agent_file.read_text()
            # Extract version and source from frontmatter
            version = None
            source = None
            for line in content.split("\n"):
                stripped_line = line.strip()
                if stripped_line.startswith("version:"):
                    version = stripped_line.split(":", 1)[1].strip()
                elif stripped_line.startswith("source:"):
                    source = stripped_line.split(":", 1)[1].strip()

            if version and source:
                print(f"    {agent_file.stem}: v{version} from {source}")
            else:
                print(f"    {agent_file.stem}: Could not extract version/source")

        return True

    finally:
        # Clean up
        import shutil

        shutil.rmtree(temp_base, ignore_errors=True)


def main():
    """Run all tests."""
    print("=" * 60)
    print("Multi-Source Agent Deployment Test Suite")
    print("=" * 60)

    # Run tests
    test1_passed = test_multi_source_discovery()
    test2_passed = test_deployment_integration()

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    if test1_passed and test2_passed:
        print("✅ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
