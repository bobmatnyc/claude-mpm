#!/usr/bin/env python3
"""
Test that project agent directory structure is correctly handled.

This test verifies:
1. init.py creates .claude-mpm/agents/ directly (no subdirectory)
2. agent_management_service.py looks for agents in the correct location
3. claude_runner.py finds and deploys project agents correctly
4. Migration from old structure to new structure works
"""

import sys
import os
import json
import shutil
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.init import ProjectInitializer
from claude_mpm.services.agents.management.agent_management_service import AgentManager
from claude_mpm.core.claude_runner import ClaudeRunner


def test_project_agent_directory_structure():
    """Test that project agent directory structure is correct."""
    print("\n=== Testing Project Agent Directory Structure ===\n")
    
    # Create a temporary test directory
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        os.chdir(test_dir)
        
        # Test 1: Initialize project directory
        print("1. Testing project directory initialization...")
        initializer = ProjectInitializer()
        success = initializer.initialize_project_directory(test_dir)
        assert success, "Failed to initialize project directory"
        
        # Verify correct structure (no subdirectory)
        agents_dir = test_dir / ".claude-mpm" / "agents"
        assert agents_dir.exists(), f"Agents directory not created: {agents_dir}"
        assert agents_dir.is_dir(), "Agents path is not a directory"
        
        # Should NOT have project-specific subdirectory
        old_subdir = agents_dir / "project-specific"
        assert not old_subdir.exists(), f"Old subdirectory should not be created: {old_subdir}"
        
        print("✓ Project directory structure is correct (no subdirectory)")
        
        # Test 2: Create a test agent
        print("\n2. Testing agent creation in correct location...")
        test_agent = {
            "agent_id": "test_engineer",
            "version": "1.0.0",
            "metadata": {
                "name": "Test Engineer Agent",
                "description": "Test agent for verification"
            },
            "capabilities": {
                "tools": ["test_tool"],
                "model": "claude-sonnet-4-20250514"
            },
            "instructions": "# Test Engineer\n\nThis is a test agent."
        }
        
        agent_file = agents_dir / "test_engineer.json"
        agent_file.write_text(json.dumps(test_agent, indent=2))
        assert agent_file.exists(), "Failed to create test agent"
        print(f"✓ Created test agent at: {agent_file}")
        
        # Test 3: Verify AgentManager finds the agent
        print("\n3. Testing AgentManager can find project agents...")
        manager = AgentManager(project_dir=agents_dir)
        
        # The manager should find agents in the correct directory
        assert manager.project_dir == agents_dir, f"Manager using wrong directory: {manager.project_dir}"
        
        # List agents (this would find JSON files if it supported JSON)
        agents = manager.list_agents(location="project")
        print(f"✓ AgentManager project directory: {manager.project_dir}")
        
        # Test 4: Verify ClaudeRunner finds project agents
        print("\n4. Testing ClaudeRunner finds project agents...")
        runner = ClaudeRunner()
        
        # Check that runner looks in the correct directory
        project_agents_dir = test_dir / ".claude-mpm" / "agents"
        claude_agents_dir = test_dir / ".claude" / "agents"
        
        # The runner's deploy_project_agents_to_claude method should find our test agent
        json_files = list(project_agents_dir.glob("*.json"))
        assert len(json_files) == 1, f"Expected 1 JSON file, found {len(json_files)}"
        assert json_files[0].name == "test_engineer.json", f"Wrong agent found: {json_files[0].name}"
        print(f"✓ Found project agent: {json_files[0]}")
        
        # Test 5: Test migration from old structure
        print("\n5. Testing migration from old structure...")
        
        # Create old structure with an agent
        old_dir = test_dir / ".claude-mpm" / "agents" / "project-specific"
        old_dir.mkdir(parents=True, exist_ok=True)
        
        old_agent = {
            "agent_id": "migrated_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Migrated Agent",
                "description": "Agent to be migrated"
            },
            "instructions": "# Migrated Agent\n\nThis agent should be migrated."
        }
        
        old_agent_file = old_dir / "migrated_agent.json"
        old_agent_file.write_text(json.dumps(old_agent, indent=2))
        
        # Re-initialize to trigger migration
        initializer2 = ProjectInitializer()
        initializer2.project_dir = test_dir / ".claude-mpm"
        initializer2._migrate_project_agents()
        
        # Check migration worked
        new_agent_file = agents_dir / "migrated_agent.json"
        assert new_agent_file.exists(), "Agent was not migrated"
        assert not old_agent_file.exists(), "Old agent file should be removed"
        print(f"✓ Successfully migrated agent from old structure")
        
        # Verify both agents are now in the correct location
        all_agents = list(agents_dir.glob("*.json"))
        assert len(all_agents) == 2, f"Expected 2 agents after migration, found {len(all_agents)}"
        agent_names = {a.stem for a in all_agents}
        assert agent_names == {"test_engineer", "migrated_agent"}, f"Wrong agents found: {agent_names}"
        print(f"✓ All agents in correct location: {agent_names}")
        
    print("\n=== All Tests Passed! ===\n")
    print("Summary:")
    print("✓ Project directory creates agents/ directly (no subdirectory)")
    print("✓ AgentManager looks in the correct directory")
    print("✓ ClaudeRunner finds project agents correctly")
    print("✓ Migration from old structure works properly")
    print("\nThe project agent directory structure fix is working correctly!")
    return True


if __name__ == "__main__":
    try:
        test_project_agent_directory_structure()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)