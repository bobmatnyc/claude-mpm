#!/usr/bin/env python3
"""
Test that PM agent is properly excluded from deployment.

The PM (Project Manager) agent must NEVER be deployed as a subagent because:
1. PM is the main Claude instance that orchestrates other agents
2. PM is not a subagent itself - it's the primary interface
3. Deploying PM as a subagent would create confusion and circular dependencies

This test ensures PM exclusion is enforced at all deployment levels.
"""

import json
import sys
import tempfile
from pathlib import Path
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService
from claude_mpm.core.claude_runner import ClaudeRunner


def test_pm_exclusion_in_deployment_service():
    """Test that AgentDeploymentService excludes PM agent."""
    print("Testing PM exclusion in AgentDeploymentService...")
    
    # Simply verify that PM is in the excluded list in the service
    service = AgentDeploymentService()
    
    # The excluded names should include PM variations
    # We can't easily test the full deployment without a proper setup,
    # but we can verify the exclusion is configured
    
    # Check that PM would be excluded by checking template loading
    with tempfile.TemporaryDirectory() as tmpdir:
        templates_dir = Path(tmpdir)
        templates_dir.mkdir(exist_ok=True)
        
        # Create test agents
        for agent_name in ["pm", "engineer", "qa"]:
            agent_data = {
                "agent_id": agent_name,
                "version": "2.0.0",
                "metadata": {"name": agent_name.title()},
                "instructions": f"{agent_name} instructions"
            }
            with open(templates_dir / f"{agent_name}.json", "w") as f:
                json.dump(agent_data, f)
        
        # Set the templates directory
        service.templates_dir = templates_dir
        
        # Load available agents (this method filters out excluded agents)
        agents = service.list_available_agents()
        agent_names = [a["name"] for a in agents]
        
        # Verify PM is excluded
        assert "pm" not in agent_names, "❌ PM agent should be excluded from available agents!"
        assert "engineer" in agent_names, "❌ Engineer should be in available agents!"
        assert "qa" in agent_names, "❌ QA should be in available agents!"
        
        print(f"✅ AgentDeploymentService excludes PM from available agents")
        print(f"   Available agents: {agent_names}")
        return True


def test_pm_exclusion_in_project_deployment():
    """Test that project deployment script excludes PM agent."""
    print("Testing PM exclusion in project deployment script...")
    
    # Import the deployment script function
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
    from deploy_project_agents import deploy_project_agents
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Set up project structure
        project_dir = Path(tmpdir) / "test_project"
        project_dir.mkdir()
        
        source_dir = project_dir / ".claude-mpm" / "agents"
        source_dir.mkdir(parents=True)
        
        target_dir = project_dir / ".claude" / "agents"
        target_dir.mkdir(parents=True)
        
        # Create PM agent in source
        pm_agent = {
            "agent_id": "pm",
            "version": "2.0.0",
            "metadata": {
                "name": "PM Agent",
                "description": "Should not be deployed"
            },
            "instructions": "PM instructions"
        }
        
        with open(source_dir / "pm.json", "w") as f:
            json.dump(pm_agent, f)
        
        # Create normal agent
        qa_agent = {
            "agent_id": "qa",
            "version": "2.0.0",
            "metadata": {
                "name": "QA Agent",
                "description": "Should be deployed"
            },
            "instructions": "QA instructions"
        }
        
        with open(source_dir / "qa.json", "w") as f:
            json.dump(qa_agent, f)
        
        # Change to project directory for deployment
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(project_dir)
            
            # Run deployment
            success = deploy_project_agents()
            
            # Check results
            deployed_files = list(target_dir.glob("*.md"))
            deployed_names = [f.stem for f in deployed_files]
            
            assert "pm" not in deployed_names, "❌ PM agent was deployed from project agents!"
            assert "qa" in deployed_names, "❌ QA agent should have been deployed!"
            
            print("✅ Project deployment script correctly excludes PM agent")
            return True
            
        finally:
            os.chdir(original_cwd)


def test_pm_never_in_claude_agents_dir():
    """Verify PM agent is not present in .claude/agents/ directory."""
    print("Checking .claude/agents/ directory...")
    
    claude_agents_dir = Path.cwd() / ".claude" / "agents"
    if claude_agents_dir.exists():
        pm_files = list(claude_agents_dir.glob("pm.*"))
        pm_files.extend(list(claude_agents_dir.glob("project_manager.*")))
        
        if pm_files:
            print(f"❌ Found PM agent files in .claude/agents/: {pm_files}")
            # Clean them up
            for f in pm_files:
                f.unlink()
                print(f"  🧹 Removed {f}")
            return False
        else:
            print("✅ No PM agent files in .claude/agents/")
            return True
    else:
        print("✅ No .claude/agents/ directory exists")
        return True


def main():
    """Run all PM exclusion tests."""
    print("=" * 60)
    print("PM AGENT EXCLUSION TEST SUITE")
    print("=" * 60)
    print()
    print("CRITICAL: PM (Project Manager) must NEVER be deployed")
    print("Reason: PM is the main Claude instance, not a subagent")
    print()
    
    all_passed = True
    
    # Test 1: Deployment Service
    try:
        if not test_pm_exclusion_in_deployment_service():
            all_passed = False
    except Exception as e:
        print(f"❌ Deployment service test failed: {e}")
        all_passed = False
    
    print()
    
    # Test 2: Project Deployment Script
    try:
        if not test_pm_exclusion_in_project_deployment():
            all_passed = False
    except Exception as e:
        print(f"❌ Project deployment test failed: {e}")
        all_passed = False
    
    print()
    
    # Test 3: Current State Check
    if not test_pm_never_in_claude_agents_dir():
        all_passed = False
    
    print()
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED - PM agent is properly excluded")
        return 0
    else:
        print("❌ SOME TESTS FAILED - PM exclusion needs attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())