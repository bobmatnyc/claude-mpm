#!/usr/bin/env python3
"""
Test script to simulate the real-world scenario where claude-mpm is invoked
from a user's project directory.

This test creates a temporary user project and verifies that:
1. System agents are deployed to user's .claude/agents/ directory
2. Project agents from user's .claude-mpm/agents/ are deployed correctly
3. The framework directory is not modified
"""

import json
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import ClaudeRunner


def create_test_project_agent(project_dir: Path):
    """Create a test project agent in the user's project directory."""
    agents_dir = project_dir / ".claude-mpm" / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)

    # Create a custom test agent
    test_agent = {
        "agent_id": "test_custom_agent",
        "version": "1.0.0",
        "metadata": {
            "name": "Test Custom Agent",
            "description": "A test agent for verification",
        },
        "capabilities": {"tools": ["custom_tool"], "model": "claude-sonnet-4-20250514"},
        "instructions": "# Test Custom Agent\\n\\nThis is a test agent for verification purposes.",
    }

    agent_file = agents_dir / "test_custom_agent.json"
    agent_file.write_text(json.dumps(test_agent, indent=2))

    return agent_file


def test_user_directory_scenario():
    """Test the complete user directory scenario."""

    print("\n=== Testing Complete User Directory Scenario ===\n")

    # Save original working directory
    original_cwd = Path.cwd()
    framework_dir = original_cwd  # The claude-mpm framework directory

    # Create a temporary user project directory
    with tmp_path as temp_dir:
        user_project = Path(temp_dir) / "user_project"
        user_project.mkdir()

        print(f"✓ Created simulated user project: {user_project}")
        print(f"✓ Framework directory: {framework_dir}")

        # Create a test project agent
        test_agent_file = create_test_project_agent(user_project)
        print(f"✓ Created test project agent: {test_agent_file}")

        # Simulate being invoked from user's project
        os.environ["CLAUDE_MPM_USER_PWD"] = str(user_project)
        print(f"✓ Set CLAUDE_MPM_USER_PWD to: {user_project}")

        # Create ClaudeRunner (this is what happens when claude-mpm runs)
        print("\n--- Initializing ClaudeRunner ---")
        runner = ClaudeRunner(enable_tickets=False, log_level="OFF")

        # Verify deployment service is using correct directory
        assert (
            runner.deployment_service.working_directory == user_project
        ), f"Expected deployment service to use {user_project}, got {runner.deployment_service.working_directory}"
        print(
            f"✓ ClaudeRunner deployment service using user directory: {runner.deployment_service.working_directory}"
        )

        # Setup agents (deploy system agents)
        print("\n--- Deploying System Agents ---")
        success = runner.setup_agents()
        assert success, "Failed to setup system agents"

        # Check where agents were deployed
        user_claude_agents = user_project / ".claude" / "agents"
        framework_claude_agents = framework_dir / ".claude" / "agents"

        print("\nChecking deployment locations:")
        print(f"  User project .claude/agents/: {user_claude_agents.exists()}")
        print(f"  Framework .claude/agents/: {framework_claude_agents.exists()}")

        # Verify agents are in user directory
        assert (
            user_claude_agents.exists()
        ), f"Agents should be deployed to {user_claude_agents}"

        system_agents = list(user_claude_agents.glob("*.md"))
        print(f"\n✓ Found {len(system_agents)} system agents in user directory:")
        for agent in system_agents[:3]:
            print(f"  - {agent.name}")

        # Deploy project agents
        print("\n--- Deploying Project Agents ---")
        success = runner.deploy_project_agents_to_claude()
        assert success, "Failed to deploy project agents"

        # Check for our custom test agent
        test_agent_md = user_claude_agents / "test_custom_agent.md"
        assert (
            test_agent_md.exists()
        ), f"Test agent should be deployed to {test_agent_md}"
        print(f"✓ Test project agent deployed: {test_agent_md}")

        # Verify content contains project marker
        content = test_agent_md.read_text()
        assert (
            "author: claude-mpm-project" in content or "source: project" in content
        ), "Project agent should have project marker"
        print("✓ Project agent has correct project marker")

        # Verify framework directory was NOT modified
        if framework_claude_agents.exists():
            list(framework_claude_agents.glob("*.md"))
            # Check that test agent is NOT in framework directory
            framework_test_agent = framework_claude_agents / "test_custom_agent.md"
            assert (
                not framework_test_agent.exists()
            ), f"Test agent should NOT be in framework directory: {framework_test_agent}"
            print("✓ Framework directory not contaminated with user agents")
        else:
            print("✓ Framework .claude/agents/ directory not created (good)")

        # Clean up
        del os.environ["CLAUDE_MPM_USER_PWD"]

        print("\n✅ User directory scenario test PASSED!")
        print(f"   - System agents deployed to: {user_claude_agents}")
        print("   - Project agents deployed correctly")
        print("   - Framework directory unchanged")


if __name__ == "__main__":
    try:
        test_user_directory_scenario()

        print("\n" + "=" * 60)
        print("✅ USER DIRECTORY SCENARIO TEST SUCCESSFUL!")
        print("=" * 60 + "\n")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
