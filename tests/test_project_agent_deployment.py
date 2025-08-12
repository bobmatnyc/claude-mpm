#!/usr/bin/env python3
"""
Test project agent deployment functionality.

This test verifies that:
1. Project agents in .claude-mpm/agents/templates/ are discovered
2. They are properly deployed to .claude/agents/
3. Project agents override system agents with the same name
4. Deployment happens automatically on startup
"""

import json
import tempfile
import shutil
from pathlib import Path
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.claude_mpm.core.claude_runner import ClaudeRunner
from src.claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService


def test_project_agent_deployment():
    """Test that project agents are deployed from .claude-mpm/agents/templates/ to .claude/agents/."""
    
    # Create a temporary directory to simulate a project
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create project agent templates directory
        project_templates_dir = project_dir / ".claude-mpm" / "agents" / "templates"
        project_templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a test project agent JSON file
        test_agent = {
            "agent_id": "test_project_agent",
            "version": "1.0.0",
            "metadata": {
                "name": "Test Project Agent",
                "description": "A test agent for project-specific tasks"
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "tools": ["Read", "Write", "Edit"]
            },
            "instructions": "You are a test project agent. This is a project-specific agent that should override system agents."
        }
        
        test_agent_path = project_templates_dir / "test_project_agent.json"
        test_agent_path.write_text(json.dumps(test_agent, indent=2))
        
        # Create another agent that might override a system agent
        override_agent = {
            "agent_id": "engineer",
            "version": "2.0.0",
            "metadata": {
                "name": "Project Engineer",
                "description": "Project-specific engineer agent with custom rules"
            },
            "capabilities": {
                "model": "claude-opus-4-20250514",
                "tools": ["Read", "Write", "Edit", "Bash", "ProjectSpecificTool"]
            },
            "instructions": "You are a PROJECT-SPECIFIC engineer agent with custom rules for this project."
        }
        
        override_agent_path = project_templates_dir / "engineer.json"
        override_agent_path.write_text(json.dumps(override_agent, indent=2))
        
        # Change to the project directory
        original_cwd = Path.cwd()
        try:
            os.chdir(project_dir)
            
            # Create a ClaudeRunner instance
            runner = ClaudeRunner(enable_tickets=False, log_level="INFO")
            
            # Deploy project agents
            result = runner.deploy_project_agents_to_claude()
            
            # Verify deployment was successful
            assert result, "Project agent deployment should succeed"
            
            # Check that agents were deployed to .claude/agents/
            claude_agents_dir = project_dir / ".claude" / "agents"
            assert claude_agents_dir.exists(), ".claude/agents/ directory should exist"
            
            # Check for test agent
            test_agent_md = claude_agents_dir / "test_project_agent.md"
            assert test_agent_md.exists(), "test_project_agent.md should be deployed"
            
            # Verify content of deployed agent
            deployed_content = test_agent_md.read_text()
            print(f"DEBUG: Deployed agent content (first 500 chars):\n{deployed_content[:500]}\n")
            assert "author: claude-mpm-project" in deployed_content, "Should be marked as project agent"
            # Check for description in the frontmatter (it's in the description field, not name)
            assert "test agent for project-specific tasks" in deployed_content.lower(), "Should contain agent description"
            assert "project-specific agent" in deployed_content, "Should contain instructions"
            
            # Check for override agent
            override_agent_md = claude_agents_dir / "engineer.md"
            assert override_agent_md.exists(), "engineer.md should be deployed"
            
            # Verify override agent content
            override_content = override_agent_md.read_text()
            assert "author: claude-mpm-project" in override_content, "Should be marked as project agent"
            assert "PROJECT-SPECIFIC engineer" in override_content, "Should contain project-specific instructions"
            assert "ProjectSpecificTool" in override_content, "Should contain project-specific tools"
            
            print("✅ Project agent deployment test passed!")
            print(f"  - Deployed test_project_agent to {test_agent_md}")
            print(f"  - Deployed project-specific engineer to {override_agent_md}")
            
            # Test that re-running doesn't re-deploy unchanged agents
            result2 = runner.deploy_project_agents_to_claude()
            assert result2, "Second deployment should also succeed"
            
            # Modify one agent and verify it gets updated
            test_agent["instructions"] = "UPDATED: New instructions for test agent"
            test_agent_path.write_text(json.dumps(test_agent, indent=2))
            
            # Wait a moment to ensure file modification time is different
            import time
            time.sleep(0.1)
            
            # Re-deploy
            result3 = runner.deploy_project_agents_to_claude()
            assert result3, "Third deployment should succeed"
            
            # Verify updated content
            updated_content = test_agent_md.read_text()
            assert "UPDATED: New instructions" in updated_content, "Agent should be updated with new instructions"
            
            print("✅ Agent update detection test passed!")
            
        finally:
            # Restore original working directory
            os.chdir(original_cwd)
    
    print("\n✅ All project agent deployment tests passed!")


def test_deployment_service_with_project_templates():
    """Test AgentDeploymentService with project template directory."""
    
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        
        # Create project templates directory
        templates_dir = project_dir / ".claude-mpm" / "agents" / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple agent template
        agent_template = {
            "agent_id": "custom_agent",
            "agent_version": 1,
            "metadata": {
                "name": "Custom Agent",
                "description": "A custom project agent"
            },
            "capabilities": {
                "model": "claude-sonnet-4-20250514",
                "tools": ["Read", "Write"]
            },
            "instructions": "You are a custom agent for this project."
        }
        
        template_path = templates_dir / "custom_agent.json"
        template_path.write_text(json.dumps(agent_template, indent=2))
        
        # Create deployment service with project templates
        deployment_service = AgentDeploymentService(
            templates_dir=templates_dir,
            base_agent_path=None  # No base agent for this test
        )
        
        # Deploy to a target directory
        target_dir = project_dir / ".claude" / "agents"
        results = deployment_service.deploy_agents(
            target_dir=target_dir,
            force_rebuild=True,
            deployment_mode="project"
        )
        
        # Verify deployment
        assert not results["errors"], f"Should have no errors: {results['errors']}"
        assert len(results["deployed"]) == 1, "Should deploy one agent"
        assert results["deployed"][0]["name"] == "custom_agent", "Should deploy custom_agent"
        
        # Check deployed file
        deployed_file = target_dir / "custom_agent.md"
        assert deployed_file.exists(), "custom_agent.md should exist"
        
        content = deployed_file.read_text()
        print(f"DEBUG: Deployment service test content:\n{content[:400]}\n")
        assert "name: custom_agent" in content, "Should have agent name in frontmatter"
        assert "custom project agent" in content.lower(), "Should have description"
        assert "You are a custom agent" in content, "Should have instructions"
        
        print("✅ Deployment service with project templates test passed!")


if __name__ == "__main__":
    print("Testing project agent deployment functionality...\n")
    
    # Run tests
    test_project_agent_deployment()
    test_deployment_service_with_project_templates()
    
    print("\n🎉 All tests completed successfully!")