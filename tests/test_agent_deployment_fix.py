#!/usr/bin/env python3
"""Test to verify the AgentDeploymentService.deploy_agent method fix."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.manager.discovery import Installation


class TestAgentDeploymentFix:
    """Test suite for the deploy_agent method fix."""
    
    def test_deploy_agent_with_path_object(self):
        """Test deploy_agent method accepts Path object as target_dir."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize the service
            service = AgentDeploymentService()
            
            # Test deploying a single agent
            agent_name = "engineer"
            
            # Call the method with a Path object (as ConfigScreenV2 does)
            result = service.deploy_agent(agent_name, temp_path)
            
            # Verify deployment succeeded
            assert result is True, "deploy_agent should return True on success"
            
            # Verify the agent file was created
            expected_file = temp_path / '.claude' / 'agents' / f'{agent_name}.md'
            assert expected_file.exists(), f"Agent file should be created at {expected_file}"
            
            # Verify file has content
            content = expected_file.read_text()
            assert len(content) > 0, "Agent file should have content"
            assert agent_name in content, f"Agent file should contain agent name '{agent_name}'"
    
    def test_deploy_agent_with_installation_path(self):
        """Test deploy_agent works with Installation.path (as used in ConfigScreenV2)."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a mock Installation object similar to ConfigScreenV2
            installation = Mock(spec=Installation)
            installation.path = temp_path
            installation.name = "test-project"
            installation.version = "1.0.0"
            
            # Initialize the service
            service = AgentDeploymentService()
            
            # Test deploying multiple agents as ConfigScreenV2 does
            agents_to_deploy = ["engineer", "qa", "documentation"]
            deployed = []
            
            for agent_name in agents_to_deploy:
                # This mimics the ConfigScreenV2 call:
                # self.agent_service.deploy_agent(agent_name, self.current_installation.path)
                result = service.deploy_agent(agent_name, installation.path)
                if result:
                    deployed.append(agent_name)
            
            # Verify all agents were deployed
            assert len(deployed) == len(agents_to_deploy), f"All agents should be deployed. Deployed: {deployed}"
            
            # Verify all agent files exist
            agents_dir = installation.path / '.claude' / 'agents'
            assert agents_dir.exists(), "Agents directory should be created"
            
            for agent_name in agents_to_deploy:
                agent_file = agents_dir / f'{agent_name}.md'
                assert agent_file.exists(), f"Agent file {agent_file} should exist"
    
    def test_deploy_agent_handles_missing_template(self):
        """Test deploy_agent handles missing agent templates gracefully."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize the service
            service = AgentDeploymentService()
            
            # Try to deploy a non-existent agent
            result = service.deploy_agent("nonexistent_agent", temp_path)
            
            # Should return False for missing template
            assert result is False, "deploy_agent should return False for missing template"
    
    def test_deploy_agent_force_rebuild(self):
        """Test deploy_agent with force_rebuild option."""
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Initialize the service
            service = AgentDeploymentService()
            agent_name = "engineer"
            
            # First deployment
            result1 = service.deploy_agent(agent_name, temp_path)
            assert result1 is True, "First deployment should succeed"
            
            agent_file = temp_path / '.claude' / 'agents' / f'{agent_name}.md'
            original_content = agent_file.read_text()
            
            # Second deployment without force (should skip)
            result2 = service.deploy_agent(agent_name, temp_path, force_rebuild=False)
            assert result2 is True, "Second deployment should return True (up to date)"
            
            # Third deployment with force
            result3 = service.deploy_agent(agent_name, temp_path, force_rebuild=True)
            assert result3 is True, "Force rebuild should succeed"
            
            # Content should still be valid
            new_content = agent_file.read_text()
            assert len(new_content) > 0, "Rebuilt file should have content"


if __name__ == "__main__":
    # Run tests
    test = TestAgentDeploymentFix()
    
    print("Running test_deploy_agent_with_path_object...")
    test.test_deploy_agent_with_path_object()
    print("✓ PASSED\n")
    
    print("Running test_deploy_agent_with_installation_path...")
    test.test_deploy_agent_with_installation_path()
    print("✓ PASSED\n")
    
    print("Running test_deploy_agent_handles_missing_template...")
    test.test_deploy_agent_handles_missing_template()
    print("✓ PASSED\n")
    
    print("Running test_deploy_agent_force_rebuild...")
    test.test_deploy_agent_force_rebuild()
    print("✓ PASSED\n")
    
    print("All tests PASSED!")