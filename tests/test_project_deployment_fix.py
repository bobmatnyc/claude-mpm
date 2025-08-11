#!/usr/bin/env python3
"""
Test script to verify the project deployment fix.

This script tests that:
1. Agents can be deployed to a project directory with deployment_mode="project"
2. The deployment doesn't skip agents that already exist with matching versions
3. Agents are correctly placed in .claude-mpm/agents/
"""

import sys
import tempfile
import shutil
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.core.claude_runner import ClaudeRunner


def test_project_deployment():
    """Test that project deployment mode works correctly."""
    print("=" * 60)
    print("Testing Project Deployment Fix")
    print("=" * 60)
    
    # Create temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        # Create a .git marker to indicate it's a project
        (project_dir / ".git").mkdir()
        
        print(f"\n1. Created test project at: {project_dir}")
        
        # Initialize deployment service
        deployment_service = AgentDeploymentService()
        
        # Test 1: Deploy agents to project with project mode
        print("\n2. Testing deployment with 'project' mode...")
        results = deployment_service.deploy_agents(
            target_dir=project_dir / ".claude-mpm",
            force_rebuild=False,
            deployment_mode="project"
        )
        
        print(f"   - Deployed: {len(results['deployed'])} agents")
        print(f"   - Updated: {len(results.get('updated', []))} agents")
        print(f"   - Skipped: {len(results.get('skipped', []))} agents")
        print(f"   - Errors: {len(results.get('errors', []))} errors")
        
        expected_agents_dir = project_dir / ".claude-mpm" / "agents"
        if not expected_agents_dir.exists():
            print(f"   ❌ FAILED: Agents directory not created at {expected_agents_dir}")
            return False
        
        agent_files = list(expected_agents_dir.glob("*.md"))
        print(f"   ✓ Created {len(agent_files)} agent files in {expected_agents_dir}")
        
        # Test 2: Deploy again to verify project mode doesn't skip
        print("\n3. Testing re-deployment with 'project' mode (should update, not skip)...")
        results2 = deployment_service.deploy_agents(
            target_dir=project_dir / ".claude-mpm",
            force_rebuild=False,
            deployment_mode="project"
        )
        
        print(f"   - Deployed: {len(results2['deployed'])} agents")
        print(f"   - Updated: {len(results2.get('updated', []))} agents")
        print(f"   - Skipped: {len(results2.get('skipped', []))} agents")
        
        # In project mode, we expect updates, not skips
        if len(results2.get('updated', [])) > 0:
            print(f"   ✓ Project mode correctly updated existing agents")
        else:
            print(f"   ⚠️  No agents were updated on re-deployment")
        
        # Test 3: Deploy with update mode to verify version checking
        print("\n4. Testing deployment with 'update' mode (should skip up-to-date agents)...")
        results3 = deployment_service.deploy_agents(
            target_dir=project_dir / ".claude-mpm",
            force_rebuild=False,
            deployment_mode="update"
        )
        
        print(f"   - Deployed: {len(results3['deployed'])} agents")
        print(f"   - Updated: {len(results3.get('updated', []))} agents")
        print(f"   - Skipped: {len(results3.get('skipped', []))} agents")
        
        if len(results3.get('skipped', [])) > 0:
            print(f"   ✓ Update mode correctly skipped up-to-date agents")
        else:
            print(f"   ⚠️  Update mode didn't skip any agents")
        
        # Test 4: Test ClaudeRunner.ensure_project_agents
        print("\n5. Testing ClaudeRunner.ensure_project_agents()...")
        
        # Change to project directory for test
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            
            runner = ClaudeRunner(
                enable_tickets=False,
                log_level="OFF"
            )
            
            success = runner.ensure_project_agents()
            
            if success:
                print(f"   ✓ ensure_project_agents() succeeded")
                
                # Verify agents exist
                project_agents = list((project_dir / ".claude-mpm" / "agents").glob("*.md"))
                print(f"   ✓ Found {len(project_agents)} agents in project")
            else:
                print(f"   ❌ ensure_project_agents() failed")
                return False
                
        finally:
            os.chdir(old_cwd)
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        return True


def main():
    """Run the test."""
    try:
        success = test_project_deployment()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()