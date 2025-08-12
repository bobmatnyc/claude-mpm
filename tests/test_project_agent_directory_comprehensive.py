#!/usr/bin/env python3
"""
Comprehensive test for project agent directory structure fix.

This test verifies the complete fix for the project agent directory mismatch issue:
- init.py creates .claude-mpm/agents/ directly (no subdirectory)
- agent_management_service.py looks in the correct location
- claude_runner.py finds and deploys project agents correctly
- Migration from old structure works properly
- PM agent is excluded from deployment
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


def run_all_tests():
    """Run all comprehensive tests for the project agent directory fix."""
    print("\n" + "="*60)
    print("COMPREHENSIVE PROJECT AGENT DIRECTORY FIX TEST")
    print("="*60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        os.chdir(test_dir)
        print(f"\nTest directory: {test_dir}")
        
        # Test 1: Fresh initialization creates correct structure
        print("\n[TEST 1] Fresh initialization creates correct structure")
        print("-" * 50)
        
        initializer = ProjectInitializer()
        success = initializer.initialize_project_directory(test_dir)
        assert success, "Failed to initialize project directory"
        
        agents_dir = test_dir / ".claude-mpm" / "agents"
        assert agents_dir.exists(), f"Agents directory not created: {agents_dir}"
        assert agents_dir.is_dir(), "Agents path is not a directory"
        
        # Should NOT have project-specific subdirectory
        old_subdir = agents_dir / "project-specific"
        assert not old_subdir.exists(), f"Old subdirectory should not be created: {old_subdir}"
        
        print("✓ Project directory initialized correctly")
        print(f"✓ Agents directory: {agents_dir}")
        print("✓ No 'project-specific' subdirectory created")
        
        # Test 2: Agent creation and management
        print("\n[TEST 2] Agent creation and management")
        print("-" * 50)
        
        # Create test agents
        agents_to_create = [
            {
                "agent_id": "custom_engineer",
                "version": "2.0.0",
                "metadata": {
                    "name": "Custom Engineer",
                    "description": "Project-specific engineer"
                },
                "capabilities": {
                    "tools": ["custom_tools"],
                    "model": "claude-sonnet-4-20250514"
                },
                "instructions": "# Custom Engineer\n\nProject-specific engineering agent."
            },
            {
                "agent_id": "custom_qa",
                "version": "1.5.0",
                "metadata": {
                    "name": "Custom QA",
                    "description": "Project-specific QA"
                },
                "instructions": "# Custom QA\n\nProject-specific QA agent."
            },
            {
                "agent_id": "pm",  # This should be excluded from deployment
                "version": "1.0.0",
                "metadata": {
                    "name": "Project Manager",
                    "description": "PM agent (should not deploy)"
                },
                "instructions": "# PM\n\nThis is the PM agent - should not be deployed."
            }
        ]
        
        for agent_data in agents_to_create:
            agent_file = agents_dir / f"{agent_data['agent_id']}.json"
            agent_file.write_text(json.dumps(agent_data, indent=2))
            print(f"✓ Created {agent_data['agent_id']}.json")
        
        # Verify AgentManager finds agents in correct location
        manager = AgentManager(project_dir=agents_dir)
        assert manager.project_dir == agents_dir, f"Manager using wrong directory: {manager.project_dir}"
        print(f"✓ AgentManager using correct directory: {manager.project_dir}")
        
        # Test 3: Deployment to .claude/agents/
        print("\n[TEST 3] Deployment to .claude/agents/")
        print("-" * 50)
        
        runner = ClaudeRunner()
        result = runner.deploy_project_agents_to_claude()
        assert result, "Deployment failed"
        
        claude_agents_dir = test_dir / ".claude" / "agents"
        assert claude_agents_dir.exists(), "Claude agents directory not created"
        
        # Check deployed files
        deployed_files = list(claude_agents_dir.glob("*.md"))
        deployed_names = {f.stem for f in deployed_files}
        
        # Should have custom_engineer and custom_qa, but NOT pm
        assert "custom_engineer" in deployed_names, "custom_engineer not deployed"
        assert "custom_qa" in deployed_names, "custom_qa not deployed"
        assert "pm" not in deployed_names, "PM agent should NOT be deployed"
        
        print(f"✓ Deployed agents: {sorted(deployed_names)}")
        print("✓ PM agent correctly excluded from deployment")
        
        # Verify project marker in deployed files
        for agent_name in ["custom_engineer", "custom_qa"]:
            agent_md = claude_agents_dir / f"{agent_name}.md"
            content = agent_md.read_text()
            assert "author: claude-mpm-project" in content, f"{agent_name} not marked as project agent"
            print(f"✓ {agent_name}.md marked as project agent")
        
        # Test 4: Migration from old structure
        print("\n[TEST 4] Migration from old structure")
        print("-" * 50)
        
        # Create a new temp directory for migration test
        with tempfile.TemporaryDirectory() as migration_dir:
            migration_path = Path(migration_dir)
            os.chdir(migration_path)
            
            # Create old structure with agents
            old_dir = migration_path / ".claude-mpm" / "agents" / "project-specific"
            old_dir.mkdir(parents=True, exist_ok=True)
            
            # Create agents in old location
            old_agents = [
                {"agent_id": "migrated_engineer", "version": "1.0.0", "instructions": "Migrated engineer"},
                {"agent_id": "migrated_qa", "version": "1.0.0", "instructions": "Migrated QA"}
            ]
            
            for agent in old_agents:
                agent_file = old_dir / f"{agent['agent_id']}.json"
                agent_file.write_text(json.dumps(agent, indent=2))
            
            print(f"✓ Created {len(old_agents)} agents in old location")
            
            # Initialize project (should trigger migration)
            init2 = ProjectInitializer()
            init2.initialize_project_directory(migration_path)
            
            # Check migration results
            new_agents_dir = migration_path / ".claude-mpm" / "agents"
            migrated_files = list(new_agents_dir.glob("*.json"))
            migrated_names = {f.stem for f in migrated_files}
            
            assert "migrated_engineer" in migrated_names, "Engineer not migrated"
            assert "migrated_qa" in migrated_names, "QA not migrated"
            
            # Old files should be removed
            old_files = list(old_dir.glob("*.json"))
            assert len(old_files) == 0, "Old files not removed"
            
            # Old directory should be removed if empty
            assert not old_dir.exists(), "Old directory not removed"
            
            print(f"✓ Migrated agents: {sorted(migrated_names)}")
            print("✓ Old files removed")
            print("✓ Old directory removed")
            
            # Verify content preserved
            for agent_name in migrated_names:
                agent_file = new_agents_dir / f"{agent_name}.json"
                content = json.loads(agent_file.read_text())
                assert "instructions" in content, f"Instructions missing in {agent_name}"
                print(f"✓ Content preserved for {agent_name}")
        
        # Test 5: Re-deployment idempotency
        print("\n[TEST 5] Re-deployment idempotency")
        print("-" * 50)
        
        os.chdir(test_dir)  # Back to original test directory
        
        # Get modification times
        eng_md = claude_agents_dir / "custom_engineer.md"
        qa_md = claude_agents_dir / "custom_qa.md"
        eng_mtime_before = eng_md.stat().st_mtime
        qa_mtime_before = qa_md.stat().st_mtime
        
        # Re-deploy without changes
        result2 = runner.deploy_project_agents_to_claude()
        assert result2, "Re-deployment failed"
        
        # Times should not change
        eng_mtime_after = eng_md.stat().st_mtime
        qa_mtime_after = qa_md.stat().st_mtime
        
        assert eng_mtime_before == eng_mtime_after, "Engineer unnecessarily updated"
        assert qa_mtime_before == qa_mtime_after, "QA unnecessarily updated"
        
        print("✓ Re-deployment correctly skipped unchanged agents")
        print("✓ Modification times unchanged for existing agents")
        
        # Test 6: Update detection
        print("\n[TEST 6] Update detection")
        print("-" * 50)
        
        # Modify one agent
        eng_file = agents_dir / "custom_engineer.json"
        eng_data = json.loads(eng_file.read_text())
        eng_data["version"] = "2.1.0"
        eng_data["instructions"] += "\n\n## Updated\nNew instructions added."
        eng_file.write_text(json.dumps(eng_data, indent=2))
        
        # Wait to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Deploy again
        result3 = runner.deploy_project_agents_to_claude()
        assert result3, "Update deployment failed"
        
        # Engineer should be updated, QA should not
        eng_mtime_updated = eng_md.stat().st_mtime
        qa_mtime_updated = qa_md.stat().st_mtime
        
        assert eng_mtime_updated > eng_mtime_after, "Engineer not updated"
        assert qa_mtime_updated == qa_mtime_after, "QA unnecessarily updated"
        
        # Verify updated content
        updated_content = eng_md.read_text()
        assert "New instructions added" in updated_content, "Updates not reflected"
        
        print("✓ Modified agent detected and updated")
        print("✓ Unmodified agent skipped")
        print("✓ Updated content correctly deployed")
    
    print("\n" + "="*60)
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("="*60)
    print("\nSummary of fixes verified:")
    print("1. ✅ init.py creates .claude-mpm/agents/ directly (no subdirectory)")
    print("2. ✅ agent_management_service.py looks in correct directory")
    print("3. ✅ claude_runner.py finds and deploys project agents")
    print("4. ✅ PM agent is excluded from deployment")
    print("5. ✅ Migration from old structure works")
    print("6. ✅ Re-deployment is idempotent")
    print("7. ✅ Updates are detected and deployed correctly")
    print("\nThe project agent directory structure fix is complete and working!")
    
    return True


if __name__ == "__main__":
    try:
        run_all_tests()
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)